import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getStoredChats, removeStoredChat, StoredChatSession } from '../services/chatStorage';

interface ChatSidebarProps {
  activeChatId?: string | null;
  onSelectChat: (chatId: string) => void;
  onNewChat: () => void;
}

const ChatSidebar: React.FC<ChatSidebarProps> = ({ activeChatId, onSelectChat, onNewChat }) => {
  const [chats, setChats] = useState<StoredChatSession[]>([]);
  const navigate = useNavigate();

  // Load chats from session storage
  useEffect(() => {
    const storedChats = getStoredChats();
    setChats(storedChats);

    // Set up listener for storage events
    const handleStorageChange = () => {
      setChats(getStoredChats());
    };

    window.addEventListener('storage', handleStorageChange);
    return () => window.removeEventListener('storage', handleStorageChange);
  }, []);

  // Manually check for changes every second
  useEffect(() => {
    const interval = setInterval(() => {
      setChats(getStoredChats());
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  const handleDeleteChat = (e: React.MouseEvent, chatId: string) => {
    e.stopPropagation();

    if (window.confirm('Are you sure you want to delete this chat?')) {
      removeStoredChat(chatId);
      setChats(getStoredChats());

      // Navigate away if we're on the deleted chat
      if (activeChatId === chatId) {
        navigate('/');
      }
    }
  };


  return (
    <div className="h-full flex flex-col bg-base-200 w-64 min-w-64 border-r">
      <div className="p-4">
        <button
          className="btn btn-primary w-full"
          onClick={onNewChat}
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M10 3a1 1 0 00-1 1v5H4a1 1 0 100 2h5v5a1 1 0 102 0v-5h5a1 1 0 100-2h-5V4a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
          New Chat
        </button>
      </div>

      <div className="h-full">
        <div className="h-1/2 flex-1 overflow-y-auto">
          {chats.length === 0 ? (
            <div className="text-center text-gray-500 p-4">
              No chat history
            </div>
          ) : (
            <ul className="menu p-2 gap-1">
              {chats.map(chat => (
                <li key={chat.id} className={`grid grid-cols-[1fr_min-content] items-center ${activeChatId === chat.id} ${activeChatId === chat.id ? 'bg-base-300 rounded-lg' : 'hover:bg-base-300 rounded-lg'}`}>
                  <div
                    className="px-3 py-2 overflow-hidden whitespace-nowrap overflow-hidden text-allipsis cursor-pointer"
                    style={{ display: 'block' }}
                    onClick={() => onSelectChat(chat.id)}
                  >
                    <div className="font-medium">{chat.title}</div>
                    {chat.lastMessage && (
                      <div className="text-xs opacity-70 truncate">{chat.lastMessage}</div>
                    )}
                  </div>
                  <button
                    className="btn btn-ghost btn-xs"
                    onClick={(e) => handleDeleteChat(e, chat.id)}
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
                    </svg>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="h-1/2 flex-1 overflow-y-auto">

          {chats.length === 0 ? (
            <div className="text-center text-gray-500 p-4">
              No chat history
            </div>
          ) : (
            <ul className="menu p-2 gap-1">
              {chats.map(chat => (
                <li key={chat.id} className={`grid grid-cols-[1fr_min-content] items-center ${activeChatId === chat.id} ${activeChatId === chat.id ? 'bg-base-300 rounded-lg' : 'hover:bg-base-300 rounded-lg'}`}>
                  <div
                    className="px-3 py-2 overflow-hidden whitespace-nowrap overflow-hidden text-allipsis cursor-pointer"
                    style={{ display: 'block' }}
                    onClick={() => onSelectChat(chat.id)}
                  >
                    <div className="font-medium">{chat.title}</div>
                    {chat.lastMessage && (
                      <div className="text-xs opacity-70 truncate">{chat.lastMessage}</div>
                    )}
                  </div>
                  <button
                    className="btn btn-ghost btn-xs"
                    onClick={(e) => handleDeleteChat(e, chat.id)}
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
                    </svg>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
};

export default ChatSidebar;
