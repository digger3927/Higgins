import os
import json
import logging
import asyncio
import httpx
import re
from typing import List, Dict, Any, Optional
from fastapi import BackgroundTasks
import google.generativeai as genai

logger = logging.getLogger("higgins-agent")

async def execute_bash(command: str, cwd: str) -> str:
    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd
        )
        stdout, stderr = await proc.communicate()
        out = stdout.decode()
        err = stderr.decode()
        if proc.returncode == 0:
            return out if out else "Command executed successfully (no output)."
        else:
            return f"Error ({proc.returncode}):\n{err}"
    except Exception as e:
        return f"Execution exception: {e}"

async def write_file_tool(path: str, content: str, cwd: str) -> str:
    try:
        full_path = os.path.join(cwd, path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully wrote to {path}"
    except Exception as e:
        return f"Failed to write file: {e}"

async def get_model_response(api_key: str, model_name: str, messages: List[Dict[str, str]], is_gemini: bool, is_local: bool):
    if is_gemini:
        genai.configure(api_key=api_key)
        contents = []
        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            contents.append({"role": role, "parts": [{"text": msg["content"]}]})
        
        clean_model = model_name.replace("google/", "") if model_name.startswith("google/") else model_name
        model = genai.GenerativeModel(clean_model)
        resp = await model.generate_content_async(contents)
        return resp.text
    elif is_local:
        OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        async with httpx.AsyncClient() as client:
            res = await client.post(
                f"{OLLAMA_HOST}/api/chat",
                json={"model": model_name, "messages": messages, "stream": False},
                timeout=120.0
            )
            if res.status_code == 200:
                return res.json().get("message", {}).get("content", "")
            return f"Ollama error: {res.text}"
    else:
        async with httpx.AsyncClient() as client:
            res = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={"model": model_name, "messages": messages},
                timeout=120.0
            )
            if res.status_code == 200:
                return res.json()["choices"][0]["message"]["content"]
            return f"OpenRouter error: {res.text}"

async def stream_agent(api_key: str, model_name: str, messages: List[Dict[str, str]], chat_id: str, sources: Optional[List[Dict[str, Any]]] = None, background_tasks: Optional[BackgroundTasks] = None, user_prompt: str = "", original_messages: Optional[List[Dict[str, str]]] = None, config: Dict[str, Any] = None, approved_tool_call: Optional[Dict[str, Any]] = None):
    from main import save_chat_messages, process_project_file_actions
    
    cwd = config.get("active_project_path") or os.getcwd()
    security_level = config.get("agent_security_level", "prompt_all")
    
    system_prompt = f"""You are Higgins, operating in AGENT MODE.
You have the ability to autonomously interact with the user's system to achieve goals.
You can use the following tools by outputting an XML block. 
You MUST stop generating and wait for the tool_result after outputting a tool call. Do NOT output multiple tool calls at once.

1. execute_bash
Description: Runs a bash command in the project directory.
Usage:
<tool name="execute_bash">
npm install
</tool>

2. write_file
Description: Writes content to a file.
Usage:
<tool name="write_file" path="relative/path.txt">
File content here
</tool>

Current Working Directory: {cwd}
"""
    
    working_messages = [m for m in messages]
    if working_messages and working_messages[0]["role"] == "system":
        working_messages[0]["content"] += "\n\n" + system_prompt
    else:
        working_messages.insert(0, {"role": "system", "content": system_prompt})
        
    is_gemini = "gemini" in model_name.lower()
    is_local = "google/" not in model_name and "anthropic/" not in model_name and "openai/" not in model_name and "meta-llama/" not in model_name and "deepseek/" not in model_name
    if not is_gemini and not api_key:
        is_local = True
        
    MAX_ITERATIONS = 5
    accumulated_final_content = ""
    
    yield f"data: {json.dumps({'type': 'agent_status', 'content': 'Starting Agent Loop...'})}\n\n"
    
    if approved_tool_call:
        tool_name = approved_tool_call.get("tool")
        tool_input = approved_tool_call.get("input", "")
        tool_path = approved_tool_call.get("path")
        
        yield f"data: {json.dumps({'type': 'agent_status', 'content': f'Executing {tool_name} (Approved)...'})}\n\n"
        
        if tool_name == "execute_bash":
            result = await execute_bash(tool_input, cwd)
        elif tool_name == "write_file":
            result = await write_file_tool(tool_path, tool_input, cwd)
        else:
            result = f"Unknown tool: {tool_name}"
            
        yield f"data: {json.dumps({'type': 'tool_result', 'tool': tool_name, 'output': result})}\n\n"
        
        if tool_path:
            xml_call = f'<tool name="{tool_name}" path="{tool_path}">\n{tool_input}\n</tool>'
        else:
            xml_call = f'<tool name="{tool_name}">\n{tool_input}\n</tool>'
            
        if len(working_messages) > 0 and working_messages[-1]["role"] == "assistant":
            working_messages[-1]["content"] = xml_call
        else:
            working_messages.append({"role": "assistant", "content": xml_call})
            
        working_messages.append({"role": "user", "content": f'<tool_result name="{tool_name}">\n{result}\n</tool_result>'})
        
        formatted_input = tool_input.replace('\\n', '\n> ')
        accumulated_final_content += f"\n> 🛠️ **Tool:** `{tool_name}`\n> ```\n> {formatted_input}\n> ```\n"
        accumulated_final_content += f"\n<details><summary>Result</summary>\n\n```\n{result}\n```\n</details>\n\n"
    
    for iteration in range(MAX_ITERATIONS):
        yield f"data: {json.dumps({'type': 'agent_status', 'content': 'Thinking...'})}\n\n"
        
        try:
            response_text = await get_model_response(api_key, model_name, working_messages, is_gemini, is_local)
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
            break
            
        working_messages.append({"role": "assistant", "content": response_text})
        
        tool_match = re.search(r'<tool\s+name="([^"]+)"(?:.*?path="([^"]+)")?>(.*?)</tool>', response_text, re.DOTALL)
        
        if tool_match:
            tool_name = tool_match.group(1)
            tool_path = tool_match.group(2)
            tool_input = tool_match.group(3).strip()
            
            yield f"data: {json.dumps({'type': 'tool_call', 'tool': tool_name, 'input': tool_input, 'path': tool_path})}\n\n"
            
            requires_approval = False
            if security_level == "prompt_all":
                requires_approval = True
            elif security_level == "safe" and tool_name in ["execute_bash", "write_file"]:
                requires_approval = True
                
            if requires_approval:
                yield f"data: {json.dumps({'type': 'tool_approval_required', 'tool': tool_name, 'input': tool_input, 'path': tool_path})}\n\n"
                break
                
            yield f"data: {json.dumps({'type': 'agent_status', 'content': f'Executing {tool_name}...'})}\n\n"
            
            if tool_name == "execute_bash":
                result = await execute_bash(tool_input, cwd)
            elif tool_name == "write_file":
                result = await write_file_tool(tool_path, tool_input, cwd)
            else:
                result = f"Unknown tool: {tool_name}"
                
            yield f"data: {json.dumps({'type': 'tool_result', 'tool': tool_name, 'output': result})}\n\n"
            working_messages.append({"role": "user", "content": f'<tool_result name="{tool_name}">\n{result}\n</tool_result>'})
            
            formatted_input = tool_input.replace('\\n', '\n> ')
            accumulated_final_content += f"\n> 🛠️ **Tool:** `{tool_name}`\n> ```\n> {formatted_input}\n> ```\n"
            accumulated_final_content += f"\n<details><summary>Result</summary>\n\n```\n{result}\n```\n</details>\n\n"
        else:
            accumulated_final_content += response_text
            yield f"data: {json.dumps({'type': 'chunk', 'content': response_text})}\n\n"
            break
            
    if accumulated_final_content:
        save_chat_messages(chat_id, original_messages or messages, accumulated_final_content, sources=sources)
        process_project_file_actions(accumulated_final_content)
        
    yield "data: [DONE]\n\n"
