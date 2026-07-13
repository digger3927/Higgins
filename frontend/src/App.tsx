import React, { useState, useEffect, useRef } from 'react';
import { 
  User, 
  Send, 
  Settings, 
  MessageSquare, 
  Eye, 
  EyeOff, 
  Cpu, 
  Sparkles, 
  Info,
  Pin,
  Archive,
  Trash2,
  ChevronDown,
  ChevronRight,
  Plus,
  Globe,
  Database,
  Folder,
  FolderOpen,
  ArrowUp
} from 'lucide-react';
import './App.css';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

interface ChatSession {
  id: string;
  title: string;
  messages: Message[];
  model: string;
  is_pinned: boolean;
  is_archived: boolean;
  created_at: number;
}

interface SettingsConfig {
  gemini_api_key: string;
  openrouter_api_key: string;
  preferred_model: string;
  enabled_openrouter_models?: string[];
  search_provider?: string;
  tavily_api_key?: string;
  brave_api_key?: string;
  google_api_key?: string;
  google_cx?: string;
  serper_api_key?: string;
  brain_directory?: string;
}

const AVAILABLE_MODELS = [
  // Gemini Models
  { id: 'google/gemini-2.5-flash', name: 'Gemini 2.5 Flash', provider: 'google' },
  { id: 'google/gemini-1.5-pro', name: 'Gemini 1.5 Pro', provider: 'google' },
  { id: 'google/gemini-1.5-flash', name: 'Gemini 1.5 Flash', provider: 'google' },
  // OpenRouter Models
  { id: 'meta-llama/llama-3-8b-instruct:free', name: 'Llama 3 8B (Free)', provider: 'openrouter' },
  { id: 'anthropic/claude-3.5-sonnet', name: 'Claude 3.5 Sonnet', provider: 'openrouter' },
  { id: 'openai/gpt-4o-mini', name: 'GPT-4o Mini', provider: 'openrouter' },
  { id: 'deepseek/deepseek-chat', name: 'DeepSeek V3', provider: 'openrouter' },
];

function App() {
  // Chats & Session State
  const [chats, setChats] = useState<ChatSession[]>([]);
  const [activeChatId, setActiveChatId] = useState<string | null>(null);
  const [models, setModels] = useState<{ id: string; name: string; provider: string }[]>(AVAILABLE_MODELS);
  
  // Rename Inline State
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameInput, setRenameInput] = useState('');
  
  // Collapsible lists
  const [isPinnedCollapsed, setIsPinnedCollapsed] = useState(false);
  const [isArchivedCollapsed, setIsArchivedCollapsed] = useState(true);

  // App Input & Streaming States
  const [input, setInput] = useState('');
  const [selectedModel, setSelectedModel] = useState('google/gemini-2.5-flash');
  const [isGenerating, setIsGenerating] = useState(false);
  const [webSearchEnabled, setWebSearchEnabled] = useState(false);
  const [localBrainEnabled, setLocalBrainEnabled] = useState(false);
  
  // Settings States
  const [settings, setSettings] = useState<SettingsConfig>({
    gemini_api_key: '',
    openrouter_api_key: '',
    preferred_model: 'google/gemini-2.5-flash',
    enabled_openrouter_models: [],
    search_provider: 'duckduckgo',
    tavily_api_key: '',
    brave_api_key: '',
    google_api_key: '',
    google_cx: '',
    serper_api_key: '',
    brain_directory: ''
  });
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [showGeminiKey, setShowGeminiKey] = useState(false);
  const [showOpenRouterKey, setShowOpenRouterKey] = useState(false);
  
  // Temp keys for the settings form
  const [geminiKeyInput, setGeminiKeyInput] = useState('');
  const [openrouterKeyInput, setOpenRouterKeyInput] = useState('');
  const [brainDirectoryInput, setBrainDirectoryInput] = useState('');
  
  // Brain status & indexing states
  const [brainStatus, setBrainStatus] = useState<{
    brain_directory: string;
    is_indexed: boolean;
    file_count: number;
    chunk_count: number;
    last_indexed: number;
  }>({
    brain_directory: '',
    is_indexed: false,
    file_count: 0,
    chunk_count: 0,
    last_indexed: 0
  });
  const [isIndexing, setIsIndexing] = useState(false);
  const [indexingMessage, setIndexingMessage] = useState('');
  
  // Folder Picker states
  const [isFolderPickerOpen, setIsFolderPickerOpen] = useState(false);
  const [pickerCurrentPath, setPickerCurrentPath] = useState('');
  const [pickerParentPath, setPickerParentPath] = useState('');
  const [pickerSubdirs, setPickerSubdirs] = useState<string[]>([]);
  const [pickerError, setPickerError] = useState('');

  // Dynamic OpenRouter catalog state
  const [activeSettingsTab, setActiveSettingsTab] = useState<'keys' | 'catalog' | 'search' | 'brain'>('keys');
  const [openRouterCatalog, setOpenRouterCatalog] = useState<{ id: string; name: string; context_length: number; prompt_price: string; completion_price: string }[]>([]);
  const [catalogSearchQuery, setCatalogSearchQuery] = useState('');
  const [isCatalogLoading, setIsCatalogLoading] = useState(false);
  const [enabledORModelsInput, setEnabledORModelsInput] = useState<string[]>([]);

  // Search Settings state
  const [searchProviderInput, setSearchProviderInput] = useState('duckduckgo');
  const [tavilyKeyInput, setTavilyKeyInput] = useState('');
  const [braveKeyInput, setBraveKeyInput] = useState('');
  const [googleKeyInput, setGoogleKeyInput] = useState('');
  const [googleCxInput, setGoogleCxInput] = useState('');
  const [serperKeyInput, setSerperKeyInput] = useState('');

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const renameInputRef = useRef<HTMLInputElement>(null);

  // Fetch settings, chats, and models on mount
  useEffect(() => {
    fetchSettings();
    fetchChats();
    fetchModels();
    fetchBrainStatus();
  }, []);

  // Auto-focus rename input
  useEffect(() => {
    if (renamingId) {
      renameInputRef.current?.focus();
      renameInputRef.current?.select();
    }
  }, [renamingId]);

  // Find active chat object
  const activeChat = chats.find(c => c.id === activeChatId) || null;

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [activeChat?.messages, isGenerating]);

  // Adjust model selector if chat changes and has a specific model
  useEffect(() => {
    if (activeChat && activeChat.model) {
      setSelectedModel(activeChat.model);
    }
  }, [activeChatId]);

  const fetchSettings = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/settings');
      if (res.ok) {
        const data = await res.json();
        setSettings(data);
        setGeminiKeyInput(data.gemini_api_key || '');
        setOpenRouterKeyInput(data.openrouter_api_key || '');
        setEnabledORModelsInput(data.enabled_openrouter_models || []);
        
        setSearchProviderInput(data.search_provider || 'duckduckgo');
        setTavilyKeyInput(data.tavily_api_key || '');
        setBraveKeyInput(data.brave_api_key || '');
        setGoogleKeyInput(data.google_api_key || '');
        setGoogleCxInput(data.google_cx || '');
        setSerperKeyInput(data.serper_api_key || '');
        setBrainDirectoryInput(data.brain_directory || '');
        
        if (data.preferred_model && !activeChatId) {
          setSelectedModel(data.preferred_model);
        }
      }
    } catch (e) {
      console.error('Failed to fetch settings from backend:', e);
    }
  };

  const fetchBrainStatus = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/brain/status');
      if (res.ok) {
        const data = await res.json();
        setBrainStatus(data);
        if (data.brain_directory) {
          setBrainDirectoryInput(data.brain_directory);
        }
      }
    } catch (e) {
      console.error('Failed to fetch brain status:', e);
    }
  };

  const handleIndexBrain = async () => {
    setIsIndexing(true);
    setIndexingMessage('Scanning and chunking files...');
    try {
      const res = await fetch('http://localhost:8000/api/brain/index', {
        method: 'POST'
      });
      const data = await res.json();
      if (res.ok) {
        setIndexingMessage(`Successfully indexed! Found ${data.file_count} files (${data.chunk_count} chunks).`);
        fetchBrainStatus();
      } else {
        setIndexingMessage(`Failed to index: ${data.detail || 'Unknown error'}`);
      }
    } catch (e) {
      setIndexingMessage(`Error calling index endpoint: ${e}`);
    } finally {
      setIsIndexing(false);
    }
  };

  const handleOpenFolderPicker = async (initialPath: string = '') => {
    setIsFolderPickerOpen(true);
    setPickerError('');
    await fetchPickerDirectory(initialPath);
  };

  const fetchPickerDirectory = async (path: string) => {
    try {
      const res = await fetch(`http://localhost:8000/api/browse?path=${encodeURIComponent(path)}`);
      const data = await res.json();
      if (res.ok) {
        setPickerCurrentPath(data.current_path);
        setPickerParentPath(data.parent_path);
        setPickerSubdirs(data.subdirectories);
        setPickerError('');
      } else {
        setPickerError(data.detail || 'Failed to list directory');
      }
    } catch (e) {
      setPickerError(`Failed to fetch directory: ${e}`);
    }
  };

  const fetchCatalog = async () => {
    setIsCatalogLoading(true);
    try {
      const res = await fetch('http://localhost:8000/api/openrouter-catalog');
      if (res.ok) {
        const data = await res.json();
        setOpenRouterCatalog(data);
      }
    } catch (e) {
      console.error('Failed to fetch OpenRouter catalog:', e);
    } finally {
      setIsCatalogLoading(false);
    }
  };

  // Auto-fetch catalog when switching to catalog tab
  useEffect(() => {
    if (isSettingsOpen && activeSettingsTab === 'catalog' && openRouterCatalog.length === 0) {
      fetchCatalog();
    }
  }, [isSettingsOpen, activeSettingsTab, openRouterCatalog.length]);

  const fetchModels = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/models');
      if (res.ok) {
        const data = await res.json();
        setModels(data);
      }
    } catch (e) {
      console.error('Failed to fetch models from backend:', e);
    }
  };

  const fetchChats = async (selectNewest: boolean = true) => {
    try {
      const res = await fetch('http://localhost:8000/api/chats');
      if (res.ok) {
        const data: ChatSession[] = await res.json();
        setChats(data);
        
        // Auto-select a chat if none is selected, or if requested
        if (data.length > 0) {
          if (selectNewest || !activeChatId) {
            // Find first active (unarchived) chat
            const firstActive = data.find(c => !c.is_archived);
            if (firstActive) {
              setActiveChatId(firstActive.id);
            } else {
              setActiveChatId(data[0].id);
            }
          }
        } else {
          // No chats, auto-create one
          handleCreateNewChat();
        }
      }
    } catch (e) {
      console.error('Failed to fetch chats:', e);
    }
  };

  const handleCreateNewChat = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/chats', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          model: selectedModel
        }),
      });
      if (res.ok) {
        const newChat = await res.json();
        setChats(prev => [newChat, ...prev]);
        setActiveChatId(newChat.id);
        setInput('');
      }
    } catch (e) {
      console.error('Failed to create new chat:', e);
    }
  };

  const handleSaveSettings = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await fetch('http://localhost:8000/api/settings', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          gemini_api_key: geminiKeyInput,
          openrouter_api_key: openrouterKeyInput,
          preferred_model: selectedModel,
          enabled_openrouter_models: enabledORModelsInput,
          search_provider: searchProviderInput,
          tavily_api_key: tavilyKeyInput,
          brave_api_key: braveKeyInput,
          google_api_key: googleKeyInput,
          google_cx: googleCxInput,
          serper_api_key: serperKeyInput,
          brain_directory: brainDirectoryInput
        }),
      });

      if (res.ok) {
        const data = await res.json();
        setSettings(data);
        setIsSettingsOpen(false);
        // Refresh sidebar models list with selected OpenRouter choices
        fetchModels();
        fetchBrainStatus();
      }
    } catch (e) {
      console.error('Failed to update settings:', e);
    }
  };

  const handleModelChange = async (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newModel = e.target.value;
    setSelectedModel(newModel);
    
    // If we have an active chat, update its model
    if (activeChatId) {
      try {
        await fetch(`http://localhost:8000/api/chats/${activeChatId}`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            model: newModel
          })
        });
        setChats(prev => prev.map(c => c.id === activeChatId ? { ...c, model: newModel } : c));
      } catch (err) {
        console.error('Failed to update chat model:', err);
      }
    }
  };

  const handleTogglePin = async (chatId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const chat = chats.find(c => c.id === chatId);
    if (!chat) return;

    try {
      const res = await fetch(`http://localhost:8000/api/chats/${chatId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          is_pinned: !chat.is_pinned
        })
      });
      if (res.ok) {
        await res.json();
        // Update state and resort (refetch is easiest to maintain sort order)
        fetchChats(false);
      }
    } catch (err) {
      console.error('Failed to toggle pin:', err);
    }
  };

  const handleToggleArchive = async (chatId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const chat = chats.find(c => c.id === chatId);
    if (!chat) return;

    try {
      const res = await fetch(`http://localhost:8000/api/chats/${chatId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          is_archived: !chat.is_archived
        })
      });
      if (res.ok) {
        // Update state
        fetchChats(false);
        // If we archived the current chat, select another one
        if (chatId === activeChatId && !chat.is_archived) {
          setActiveChatId(null);
        }
      }
    } catch (err) {
      console.error('Failed to toggle archive:', err);
    }
  };

  const handleDeleteChat = async (chatId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm('Are you sure you want to delete this chat permanently?')) return;

    try {
      const res = await fetch(`http://localhost:8000/api/chats/${chatId}`, {
        method: 'DELETE'
      });
      if (res.ok) {
        setChats(prev => prev.filter(c => c.id !== chatId));
        if (chatId === activeChatId) {
          setActiveChatId(null);
        }
      }
    } catch (err) {
      console.error('Failed to delete chat:', err);
    }
  };

  const startRename = (chatId: string, title: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setRenamingId(chatId);
    setRenameInput(title);
  };

  const handleRenameSubmit = async (chatId: string) => {
    if (!renameInput.trim()) {
      setRenamingId(null);
      return;
    }
    
    try {
      const res = await fetch(`http://localhost:8000/api/chats/${chatId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          title: renameInput.trim()
        })
      });
      if (res.ok) {
        setChats(prev => prev.map(c => c.id === chatId ? { ...c, title: renameInput.trim() } : c));
      }
    } catch (err) {
      console.error('Failed to rename chat:', err);
    } finally {
      setRenamingId(null);
    }
  };

  const handleRenameKeyDown = (chatId: string, e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleRenameSubmit(chatId);
    } else if (e.key === 'Escape') {
      setRenamingId(null);
    }
  };

  const handleSend = async () => {
    if (!input.trim() || isGenerating || !activeChatId) return;

    const userMessage: Message = { role: 'user', content: input };
    const updatedMessages = [...(activeChat?.messages || []), userMessage];
    
    // Optimistically update the UI chat history with user prompt
    setChats(prev => prev.map(c => {
      if (c.id === activeChatId) {
        return {
          ...c,
          messages: [...c.messages, userMessage]
        };
      }
      return c;
    }));
    setInput('');
    setIsGenerating(true);

    // Add placeholder assistant message that we will stream into
    setChats(prev => prev.map(c => {
      if (c.id === activeChatId) {
        return {
          ...c,
          messages: [...c.messages, { role: 'assistant', content: '' }]
        };
      }
      return c;
    }));

    try {
      const response = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          chat_id: activeChatId,
          messages: updatedMessages,
          model: selectedModel,
          web_search_enabled: webSearchEnabled,
          local_brain_enabled: localBrainEnabled
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to connect to assistant');
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      if (!reader) throw new Error('No readable response stream');

      let done = false;
      let buffer = '';

      while (!done) {
        const { value, done: doneReading } = await reader.read();
        done = doneReading;
        buffer += decoder.decode(value, { stream: !done });

        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // Keep partial line in buffer

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const dataStr = line.slice(6).trim();
            if (dataStr === '[DONE]') {
              done = true;
              break;
            }

            try {
              const data = JSON.parse(dataStr);
              if (data.type === 'chunk') {
                setChats(prev => prev.map(c => {
                  if (c.id === activeChatId) {
                    const copyMessages = [...c.messages];
                    const lastIdx = copyMessages.length - 1;
                    copyMessages[lastIdx] = {
                      ...copyMessages[lastIdx],
                      content: copyMessages[lastIdx].content + data.content
                    };
                    return { ...c, messages: copyMessages };
                  }
                  return c;
                }));
              } else if (data.type === 'error') {
                throw new Error(data.content);
              }
            } catch (jsonErr) {
              console.error('Error parsing SSE json chunk:', jsonErr);
            }
          }
        }
      }
      
      // Reload chats list to update auto-generated titles
      fetchChats(false);
      
    } catch (err: any) {
      console.error('Chat error:', err);
      setChats(prev => prev.map(c => {
        if (c.id === activeChatId) {
          const copyMessages = [...c.messages];
          const lastIdx = copyMessages.length - 1;
          copyMessages[lastIdx] = {
            role: 'assistant',
            content: `Error: ${err.message || 'Something went wrong during generation.'}`
          };
          return { ...c, messages: copyMessages };
        }
        return c;
      }));
    } finally {
      setIsGenerating(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Helper to check if api key is configured for the selected model
  const isKeyConfigured = () => {
    const activeModelObj = models.find(m => m.id === selectedModel);
    if (!activeModelObj) return false;
    
    if (activeModelObj.provider === 'ollama') {
      return true; // Local models don't need cloud API keys!
    }
    if (activeModelObj.provider === 'google') {
      return !!settings.gemini_api_key;
    }
    if (activeModelObj.provider === 'openrouter') {
      return !!settings.openrouter_api_key;
    }
    return false;
  };

  // Grouped chats
  const pinnedChats = chats.filter(c => c.is_pinned && !c.is_archived);
  const activeChats = chats.filter(c => !c.is_pinned && !c.is_archived);
  const archivedChats = chats.filter(c => c.is_archived);

  // Render a chat item in the sidebar
  const renderChatItem = (chat: ChatSession) => {
    const isActive = chat.id === activeChatId;
    const isRenaming = chat.id === renamingId;

    return (
      <div 
        key={chat.id} 
        className={`chat-list-item ${isActive ? 'active' : ''}`}
        onClick={() => {
          if (!isRenaming) {
            setActiveChatId(chat.id);
          }
        }}
        onDoubleClick={(e) => startRename(chat.id, chat.title, e)}
      >
        <div className="chat-item-title-container">
          <MessageSquare size={14} className="nav-item-icon" />
          {isRenaming ? (
            <input
              ref={renameInputRef}
              className="chat-title-input"
              value={renameInput}
              onChange={e => setRenameInput(e.target.value)}
              onBlur={() => handleRenameSubmit(chat.id)}
              onKeyDown={(e) => handleRenameKeyDown(chat.id, e)}
              onClick={e => e.stopPropagation()}
            />
          ) : (
            <span className="chat-item-title">{chat.title}</span>
          )}
        </div>
        
        {!isRenaming && (
          <div className="chat-item-actions">
            <button 
              className={`chat-action-btn ${chat.is_pinned ? 'active' : ''}`}
              title={chat.is_pinned ? "Unpin Chat" : "Pin Chat"}
              onClick={(e) => handleTogglePin(chat.id, e)}
            >
              <Pin size={12} style={{ transform: chat.is_pinned ? 'rotate(45deg)' : 'none' }} />
            </button>
            <button 
              className="chat-action-btn"
              title={chat.is_archived ? "Restore Chat" : "Archive Chat"}
              onClick={(e) => handleToggleArchive(chat.id, e)}
            >
              <Archive size={12} />
            </button>
            <button 
              className="chat-action-btn"
              title="Delete Chat"
              onClick={(e) => handleDeleteChat(chat.id, e)}
            >
              <Trash2 size={12} />
            </button>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="workspace-container">
      {/* Sidebar */}
      <aside className="sidebar glass-panel">
        <div className="logo-section">
          <div className="logo-icon">
            <Sparkles size={18} color="white" />
          </div>
          <span className="logo-text">Higgins</span>
        </div>

        <button 
          className="new-chat-btn"
          onClick={handleCreateNewChat}
        >
          <Plus size={16} />
          <span>New Chat</span>
        </button>

        <div className="sidebar-divider"></div>

        {/* Model Selector */}
        <div className="model-selector-container">
          <div className="sidebar-label">Active Model</div>
          <select 
            className="custom-select" 
            value={selectedModel} 
            onChange={handleModelChange}
          >
            {models.filter(m => m.provider === 'ollama').length > 0 && (
              <optgroup label="Local Models (Ollama)">
                {models.filter(m => m.provider === 'ollama').map(m => (
                  <option key={m.id} value={m.id}>
                    {m.name}
                  </option>
                ))}
              </optgroup>
            )}
            {models.filter(m => m.provider !== 'ollama').length > 0 && (
              <optgroup label="Cloud Models (API)">
                {models.filter(m => m.provider !== 'ollama').map(m => (
                  <option key={m.id} value={m.id}>
                    {m.name}
                  </option>
                ))}
              </optgroup>
            )}
          </select>
        </div>

        {/* Conversations Lists */}
        <div className="chats-section">
          {/* Pinned Chats */}
          {pinnedChats.length > 0 && (
            <div className="chats-group">
              <div 
                className="group-header"
                onClick={() => setIsPinnedCollapsed(!isPinnedCollapsed)}
              >
                <span>Pinned</span>
                {isPinnedCollapsed ? <ChevronRight size={12} /> : <ChevronDown size={12} />}
              </div>
              {!isPinnedCollapsed && pinnedChats.map(renderChatItem)}
            </div>
          )}

          {/* Active Chats */}
          <div className="chats-group">
            <div className="group-header">
              <span>Recent Chats</span>
            </div>
            {activeChats.length === 0 && pinnedChats.length === 0 ? (
              <div style={{ fontSize: '12px', color: 'var(--text-muted)', padding: '6px 12px' }}>
                No active conversations
              </div>
            ) : (
              activeChats.map(renderChatItem)
            )}
          </div>

          {/* Archived Chats */}
          {archivedChats.length > 0 && (
            <div className="chats-group" style={{ marginTop: '8px' }}>
              <div 
                className="group-header"
                onClick={() => setIsArchivedCollapsed(!isArchivedCollapsed)}
              >
                <span>Archived ({archivedChats.length})</span>
                {isArchivedCollapsed ? <ChevronRight size={12} /> : <ChevronDown size={12} />}
              </div>
              {!isArchivedCollapsed && archivedChats.map(renderChatItem)}
            </div>
          )}
        </div>

        {/* Sidebar Footer */}
        <div className="sidebar-footer">
          <button 
            className="settings-btn"
            onClick={() => setIsSettingsOpen(true)}
          >
            <Settings size={16} />
            <span>API Settings</span>
          </button>
        </div>
      </aside>

      {/* Main Workspace */}
      <main className="chat-workspace">
        <header className="chat-header">
          <div className="header-model-info">
            <Cpu size={16} className="nav-item-icon" />
            <span className="header-model-title">
              {models.find(m => m.id === selectedModel)?.name || selectedModel}
            </span>
            <span className={`api-status-pill ${isKeyConfigured() ? '' : 'missing'}`}>
              <span className="pulse-dot" style={{ backgroundColor: isKeyConfigured() ? 'var(--accent-green)' : 'var(--accent-red)', boxShadow: `0 0 8px ${isKeyConfigured() ? 'var(--accent-green)' : 'var(--accent-red)'}` }}></span>
              {models.find(m => m.id === selectedModel)?.provider === 'ollama' 
                ? 'Ollama Local' 
                : isKeyConfigured() ? 'API Ready' : 'API Key Missing'}
            </span>
          </div>

          <div style={{ color: 'var(--text-muted)', fontSize: '13px', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Info size={14} />
            <span>Local Storage Active</span>
          </div>
        </header>

        {/* Message Area */}
        <div className="messages-container">
          {!activeChat || activeChat.messages.length === 0 ? (
            <div className="chat-empty-state">
              <img src="/Higgins.png" alt="Higgins" className="empty-state-icon" style={{ borderRadius: '50%', objectFit: 'cover', opacity: 0.9 }} />
              <h2 className="empty-state-title">Meet Higgins</h2>
              <p className="empty-state-subtitle">
                Your AI assistant running locally. Set up your API Keys in the settings pane below to start chatting.
              </p>
              {!isKeyConfigured() && (
                <button 
                  className="btn-primary" 
                  onClick={() => setIsSettingsOpen(true)}
                  style={{ marginTop: '8px' }}
                >
                  Configure API Keys
                </button>
              )}
            </div>
          ) : (
            activeChat.messages.map((msg, idx) => (
              <div key={idx} className={`message-row ${msg.role} animate-fade-in`}>
                <div className="message-bubble">
                  <div className="message-meta">
                    {msg.role === 'user' ? (
                      <User size={12} />
                    ) : (
                      <img 
                        src="/Higgins.png" 
                        alt="Higgins" 
                        style={{ width: '12px', height: '12px', borderRadius: '50%', objectFit: 'cover' }} 
                      />
                    )}
                    <span>{msg.role === 'user' ? 'You' : 'Higgins'}</span>
                  </div>
                  <div style={{ whiteSpace: 'pre-wrap' }}>
                    {msg.content}
                  </div>
                </div>
              </div>
            ))
          )}

          {isGenerating && activeChat?.messages[activeChat.messages.length - 1]?.content === '' && (
            <div className="message-row assistant">
              <div className="message-bubble">
                <div className="message-meta">
                  <img 
                    src="/Higgins.png" 
                    alt="Higgins" 
                    style={{ width: '12px', height: '12px', borderRadius: '50%', objectFit: 'cover' }} 
                  />
                  <span>Higgins</span>
                </div>
                <div className="typing-indicator">
                  <div className="typing-dot"></div>
                  <div className="typing-dot"></div>
                  <div className="typing-dot"></div>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Panel */}
        <div className="chat-input-container">
          <div className="input-box-wrapper glass-panel">
            <textarea
              className="chat-textarea"
              placeholder={isKeyConfigured() ? "Ask Higgins anything..." : "Please configure API keys first..."}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyPress}
              disabled={!isKeyConfigured() || isGenerating || !activeChatId}
            />
            <div className="chat-controls">
              <div className="chat-input-hints" style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                <button
                  type="button"
                  className={`search-toggle-btn ${webSearchEnabled ? 'active' : ''}`}
                  title="Toggle Web Search"
                  onClick={() => setWebSearchEnabled(!webSearchEnabled)}
                  disabled={!isKeyConfigured() || isGenerating || !activeChatId}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    color: webSearchEnabled ? 'var(--accent-blue)' : 'var(--text-muted)',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px',
                    fontSize: '12px',
                    fontWeight: 500,
                    padding: '2px 6px',
                    borderRadius: '4px',
                    transition: 'var(--transition-smooth)'
                  }}
                >
                  <Globe size={14} className={webSearchEnabled ? 'pulse-icon' : ''} />
                  <span>Web Search</span>
                </button>

                <button
                  type="button"
                  className={`search-toggle-btn ${localBrainEnabled ? 'active-purple' : ''}`}
                  title="Toggle Local Brain Search"
                  onClick={() => setLocalBrainEnabled(!localBrainEnabled)}
                  disabled={!isKeyConfigured() || isGenerating || !activeChatId}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    color: localBrainEnabled ? 'var(--accent-purple)' : 'var(--text-muted)',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px',
                    fontSize: '12px',
                    fontWeight: 500,
                    padding: '2px 6px',
                    borderRadius: '4px',
                    transition: 'var(--transition-smooth)'
                  }}
                >
                  <Database size={14} className={localBrainEnabled ? 'pulse-icon-purple' : ''} />
                  <span>Local Brain</span>
                </button>

                <span className="sidebar-divider-v" style={{ width: '1px', height: '12px', background: 'var(--border-glass)' }}></span>
                <span>Enter to send</span>
                <span>Shift + Enter for new line</span>
              </div>
              <button 
                className="send-button"
                onClick={handleSend}
                disabled={!input.trim() || isGenerating || !isKeyConfigured() || !activeChatId}
              >
                <Send size={14} />
              </button>
            </div>
          </div>
        </div>
      </main>

      {/* Settings Modal */}
      {isSettingsOpen && (
        <div className="modal-overlay">
          <div className="modal-content glass-panel" style={{ display: 'flex', flexDirection: 'column' }}>
            <div className="modal-header" style={{ marginBottom: '12px' }}>
              <h3 className="modal-title">Settings</h3>
              <button 
                className="close-btn"
                onClick={() => setIsSettingsOpen(false)}
              >
                &times;
              </button>
            </div>

            <div className="modal-tabs">
              <button 
                type="button"
                className={`modal-tab-btn ${activeSettingsTab === 'keys' ? 'active' : ''}`}
                onClick={() => setActiveSettingsTab('keys')}
              >
                API Keys
              </button>
              <button 
                type="button"
                className={`modal-tab-btn ${activeSettingsTab === 'catalog' ? 'active' : ''}`}
                onClick={() => setActiveSettingsTab('catalog')}
              >
                OpenRouter Catalog
              </button>
              <button 
                type="button"
                className={`modal-tab-btn ${activeSettingsTab === 'search' ? 'active' : ''}`}
                onClick={() => setActiveSettingsTab('search')}
              >
                Search Engines
              </button>
              <button 
                type="button"
                className={`modal-tab-btn ${activeSettingsTab === 'brain' ? 'active' : ''}`}
                onClick={() => setActiveSettingsTab('brain')}
              >
                Local Brain
              </button>
            </div>

            <form onSubmit={handleSaveSettings} style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
              {activeSettingsTab === 'keys' ? (
                <div style={{ flex: 1 }}>
                  <div className="form-group">
                     <label className="form-label">Gemini API Key</label>
                     <div className="form-input-wrapper">
                       <input
                         type={showGeminiKey ? "text" : "password"}
                         className="form-input"
                         placeholder="AIzaSy..."
                         value={geminiKeyInput}
                         onChange={e => setGeminiKeyInput(e.target.value)}
                       />
                       <button
                         type="button"
                         className="form-input-icon-btn"
                         onClick={() => setShowGeminiKey(!showGeminiKey)}
                       >
                         {showGeminiKey ? <EyeOff size={16} /> : <Eye size={16} />}
                       </button>
                     </div>
                     <span className="form-hint">
                       Used for Google Gemini models (e.g. Gemini 2.5 Flash, Gemini 1.5 Pro).
                     </span>
                  </div>

                  <div className="form-group" style={{ marginTop: '16px' }}>
                     <label className="form-label">OpenRouter API Key</label>
                     <div className="form-input-wrapper">
                       <input
                         type={showOpenRouterKey ? "text" : "password"}
                         className="form-input"
                         placeholder="sk-or-v1-..."
                         value={openrouterKeyInput}
                         onChange={e => setOpenRouterKeyInput(e.target.value)}
                       />
                       <button
                         type="button"
                         className="form-input-icon-btn"
                         onClick={() => setShowOpenRouterKey(!showOpenRouterKey)}
                       >
                         {showOpenRouterKey ? <EyeOff size={16} /> : <Eye size={16} />}
                       </button>
                     </div>
                     <span className="form-hint">
                       Used for OpenRouter models (e.g. Llama 3, Claude 3.5, DeepSeek).
                     </span>
                  </div>
                </div>
              ) : activeSettingsTab === 'search' ? (
                <div style={{ flex: 1 }}>
                  <div className="form-group">
                    <label className="form-label">Search Provider</label>
                    <select
                      className="custom-select"
                      value={searchProviderInput}
                      onChange={e => setSearchProviderInput(e.target.value)}
                    >
                      <option value="duckduckgo">DuckDuckGo (Free / No Key)</option>
                      <option value="tavily">Tavily API</option>
                      <option value="brave">Brave Search API</option>
                      <option value="google">Google Custom Search API</option>
                      <option value="serper">Serper API</option>
                    </select>
                  </div>

                  {searchProviderInput === 'duckduckgo' && (
                    <div style={{ marginTop: '16px', fontSize: '13px', color: 'var(--text-secondary)', background: 'rgba(255,255,255,0.02)', padding: '12px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-glass)', lineHeight: 1.5 }}>
                      <strong>DuckDuckGo Crawling Active:</strong>
                      <p style={{ marginTop: '4px' }}>No keys are needed. Higgins will fetch web results using a built-in search parser automatically.</p>
                    </div>
                  )}

                  {searchProviderInput === 'tavily' && (
                    <div className="form-group" style={{ marginTop: '16px' }}>
                      <label className="form-label">Tavily API Key</label>
                      <input
                        type="password"
                        className="form-input"
                        placeholder="tvly-..."
                        value={tavilyKeyInput}
                        onChange={e => setTavilyKeyInput(e.target.value)}
                      />
                      <span className="form-hint">
                        Used to run search optimized summaries. Get a key at tavily.com.
                      </span>
                    </div>
                  )}

                  {searchProviderInput === 'brave' && (
                    <div className="form-group" style={{ marginTop: '16px' }}>
                      <label className="form-label">Brave Search API Key</label>
                      <input
                        type="password"
                        className="form-input"
                        placeholder="BSAsy..."
                        value={braveKeyInput}
                        onChange={e => setBraveKeyInput(e.target.value)}
                      />
                      <span className="form-hint">
                        Used to fetch independent web results. Get a key at brave.com/search/api.
                      </span>
                    </div>
                  )}

                  {searchProviderInput === 'google' && (
                    <div style={{ marginTop: '16px' }}>
                      <div className="form-group">
                        <label className="form-label">Google Developers API Key</label>
                        <input
                          type="password"
                          className="form-input"
                          placeholder="AIzaSy..."
                          value={googleKeyInput}
                          onChange={e => setGoogleKeyInput(e.target.value)}
                        />
                      </div>
                      <div className="form-group" style={{ marginTop: '12px' }}>
                        <label className="form-label">Google Custom Search Engine ID (CX)</label>
                        <input
                          type="text"
                          className="form-input"
                          placeholder="0123456789..."
                          value={googleCxInput}
                          onChange={e => setGoogleCxInput(e.target.value)}
                        />
                      </div>
                    </div>
                  )}

                  {searchProviderInput === 'serper' && (
                    <div className="form-group" style={{ marginTop: '16px' }}>
                      <label className="form-label">Serper API Key</label>
                      <input
                        type="password"
                        className="form-input"
                        placeholder="serper-..."
                        value={serperKeyInput}
                        onChange={e => setSerperKeyInput(e.target.value)}
                      />
                      <span className="form-hint">
                        Google Search scraping engine. Get a key at serper.dev.
                      </span>
                    </div>
                  )}
                </div>
              ) : activeSettingsTab === 'brain' ? (
                <div style={{ flex: 1 }}>
                  <div className="form-group">
                    <label className="form-label">Local Brain Folder Path</label>
                    <div className="form-input-wrapper" style={{ display: 'flex', gap: '8px' }}>
                      <input
                        type="text"
                        className="form-input"
                        placeholder="/absolute/path/to/your/documents/folder"
                        value={brainDirectoryInput}
                        onChange={e => setBrainDirectoryInput(e.target.value)}
                        style={{ flex: 1 }}
                      />
                      <button
                        type="button"
                        className="btn-secondary"
                        onClick={() => handleOpenFolderPicker(brainDirectoryInput)}
                        style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '0 16px', fontSize: '13px', whiteSpace: 'nowrap' }}
                      >
                        <Folder size={14} />
                        Browse
                      </button>
                    </div>
                    <span className="form-hint">
                      Higgins will index and scan all text files, markdown files, and PDF documents in this directory recursively.
                    </span>
                  </div>
                  
                  <div style={{ marginTop: '20px', background: 'rgba(255,255,255,0.02)', padding: '16px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-glass)' }}>
                    <h4 style={{ margin: 0, fontSize: '14px', color: 'var(--text-primary)' }}>Brain Statistics</h4>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '12px', marginTop: '12px', fontSize: '13px' }}>
                      <div>
                        <span style={{ color: 'var(--text-muted)' }}>Status: </span>
                        <span style={{ color: brainStatus.is_indexed ? 'var(--accent-green)' : 'var(--accent-red)', fontWeight: 500 }}>
                          {brainStatus.is_indexed ? 'Indexed' : 'Not Indexed'}
                        </span>
                      </div>
                      <div>
                        <span style={{ color: 'var(--text-muted)' }}>Last Scan: </span>
                        <span>
                          {brainStatus.last_indexed > 0 
                            ? new Date(brainStatus.last_indexed * 1000).toLocaleString() 
                            : 'Never'}
                        </span>
                      </div>
                      <div>
                        <span style={{ color: 'var(--text-muted)' }}>Total Files: </span>
                        <span>{brainStatus.file_count}</span>
                      </div>
                      <div>
                        <span style={{ color: 'var(--text-muted)' }}>Context Chunks: </span>
                        <span>{brainStatus.chunk_count}</span>
                      </div>
                    </div>
                    
                    <div style={{ marginTop: '16px', display: 'flex', alignItems: 'center', gap: '12px' }}>
                      <button
                        type="button"
                        className="btn-secondary"
                        onClick={handleIndexBrain}
                        disabled={isIndexing || !brainDirectoryInput.trim()}
                        style={{ padding: '6px 12px', fontSize: '13px' }}
                      >
                        {isIndexing ? 'Indexing...' : 'Index Directory Now'}
                      </button>
                      {indexingMessage && (
                        <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                          {indexingMessage}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              ) : (
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
                  <div className="catalog-search-wrapper">
                    <input
                      type="text"
                      className="form-input"
                      placeholder="Search OpenRouter models..."
                      value={catalogSearchQuery}
                      onChange={e => setCatalogSearchQuery(e.target.value)}
                    />
                  </div>

                  {isCatalogLoading ? (
                    <div style={{ padding: '40px 0', textAlign: 'center', color: 'var(--text-secondary)' }}>
                      Loading OpenRouter catalog...
                    </div>
                  ) : (
                    <div className="catalog-list-container">
                      {openRouterCatalog
                        .filter(m => 
                          m.name.toLowerCase().includes(catalogSearchQuery.toLowerCase()) || 
                          m.id.toLowerCase().includes(catalogSearchQuery.toLowerCase())
                        )
                        .map(model => {
                          const isChecked = enabledORModelsInput.includes(model.id);
                          const isFree = model.id.includes(':free');
                          
                          return (
                            <div 
                              key={model.id} 
                              className="catalog-item-row"
                              onClick={() => {
                                setEnabledORModelsInput(prev => 
                                  isChecked 
                                    ? prev.filter(id => id !== model.id)
                                    : [...prev, model.id]
                                );
                              }}
                            >
                              <div className="catalog-item-left">
                                <input
                                  type="checkbox"
                                  className="catalog-checkbox"
                                  checked={isChecked}
                                  onChange={() => {}} // Handled by row onClick
                                />
                                <div className="catalog-model-info-text">
                                  <span className="catalog-model-name">{model.name}</span>
                                  <span className="catalog-model-id">{model.id}</span>
                                </div>
                              </div>
                              <div className="catalog-item-right">
                                {isFree && <span className="catalog-badge free">Free</span>}
                                {model.context_length > 0 && (
                                  <span className="catalog-badge">
                                    {Math.round(model.context_length / 1000)}k ctx
                                  </span>
                                )}
                              </div>
                            </div>
                          );
                        })}
                      {openRouterCatalog.length > 0 && openRouterCatalog.filter(m => 
                        m.name.toLowerCase().includes(catalogSearchQuery.toLowerCase()) || 
                        m.id.toLowerCase().includes(catalogSearchQuery.toLowerCase())
                      ).length === 0 && (
                        <div style={{ padding: '20px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>
                          No models matching your search
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              <div className="modal-actions">
                <button 
                  type="button" 
                  className="btn-secondary"
                  onClick={() => setIsSettingsOpen(false)}
                >
                  Cancel
                </button>
                <button 
                  type="submit" 
                  className="btn-primary"
                >
                  Save Config
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
      
      {/* Folder Picker Modal */}
      {isFolderPickerOpen && (
        <div className="modal-overlay" style={{ zIndex: 1100 }}>
          <div className="modal-content glass-panel" style={{ maxWidth: '600px', display: 'flex', flexDirection: 'column', height: '80vh' }}>
            <div className="modal-header">
               <h3 className="modal-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                 <FolderOpen size={18} color="var(--accent-purple)" />
                 Select Local Brain Directory
               </h3>
              <button 
                className="close-btn"
                onClick={() => setIsFolderPickerOpen(false)}
              >
                &times;
              </button>
            </div>
            
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0, padding: '16px 0' }}>
              {/* Current Path Bar */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '0 16px 12px 16px', borderBottom: '1px solid var(--border-glass)' }}>
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => fetchPickerDirectory(pickerParentPath)}
                  disabled={!pickerParentPath}
                  style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '6px 8px' }}
                  title="Go up to parent directory"
                >
                  <ArrowUp size={14} />
                </button>
                <input
                  type="text"
                  className="form-input"
                  readOnly
                  value={pickerCurrentPath}
                  style={{ flex: 1, cursor: 'default', background: 'rgba(255,255,255,0.02)' }}
                />
              </div>
              
              {/* Error alert */}
              {pickerError && (
                <div style={{ margin: '12px 16px', color: 'var(--accent-red)', fontSize: '13px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Info size={14} />
                  <span>{pickerError}</span>
                </div>
              )}
              
              {/* Folder List */}
              <div 
                className="catalog-list-container" 
                style={{ 
                  flex: 1, 
                  overflowY: 'auto', 
                  padding: '12px 16px', 
                  display: 'flex', 
                  flexDirection: 'column', 
                  gap: '4px' 
                }}
              >
                {pickerSubdirs.length === 0 ? (
                  <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '40px 0', fontSize: '13px' }}>
                    No subdirectories found
                  </div>
                ) : (
                  pickerSubdirs.map((dir) => (
                    <div
                      key={dir}
                      className="catalog-item-row"
                      style={{ padding: '8px 12px', borderRadius: 'var(--radius-sm)' }}
                      onDoubleClick={() => fetchPickerDirectory(pickerCurrentPath + '/' + dir)}
                      onClick={() => {}}
                    >
                      <div className="catalog-item-left" style={{ cursor: 'pointer' }} onDoubleClick={() => fetchPickerDirectory(pickerCurrentPath + '/' + dir)}>
                        <Folder size={16} color="var(--accent-purple)" style={{ marginRight: '8px' }} />
                        <span className="catalog-model-name" style={{ fontSize: '13px' }}>{dir}</span>
                      </div>
                      <button
                        type="button"
                        className="chat-action-btn"
                        onClick={() => fetchPickerDirectory(pickerCurrentPath + '/' + dir)}
                        style={{ fontSize: '11px', color: 'var(--text-muted)' }}
                      >
                        Open
                      </button>
                    </div>
                  ))
                )}
              </div>
            </div>
            
            <div className="modal-actions" style={{ borderTop: '1px solid var(--border-glass)', paddingTop: '12px' }}>
              <button
                type="button"
                className="btn-secondary"
                onClick={() => setIsFolderPickerOpen(false)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn-primary"
                style={{ background: 'var(--accent-purple)', borderColor: 'var(--accent-purple)' }}
                onClick={() => {
                  setBrainDirectoryInput(pickerCurrentPath);
                  setIsFolderPickerOpen(false);
                }}
              >
                Select Current Folder
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
