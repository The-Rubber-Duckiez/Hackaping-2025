import React, { useState, useEffect, useRef, useMemo } from 'react';
import { ApiClientRest } from '../rest/api_client_rest';
import { createChatApi, Message, Source } from '../rest/modules/chat';
import { updateChatLastMessage } from '../services/chatStorage';

interface ChatProps {
  chatId: string;
  client: ApiClientRest;
}

const sendFeedback = async (messageId: number, feedback: string) => {
  try {
    await fetch('/api/messages/feedback', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message_id: messageId, feedback }),
    });
    alert('Feedback submitted successfully!');
  } catch (error) {
    console.error('Error submitting feedback:', error);
    alert('Failed to submit feedback.');
  }
};

const Chat: React.FC<ChatProps> = ({ chatId, client }) => {
  const chatApi = useMemo(() => createChatApi(client), [client]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [showSources, setShowSources] = useState(false);
  const [selectedMessageIndex, setSelectedMessageIndex] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // We don't need any URL or pending message checking anymore
  // The WelcomeScreen component awaits the response before navigating here

  // Load chat history when chatId changes
  useEffect(() => {
    if (!chatId) return;

    const loadChatHistory = async () => {
      try {
        const chatMessages = await chatApi.getChatMessages(chatId);

        // Convert assistant to bot for rendering
        const formattedMessages = chatMessages.map(msg => ({
          ...msg,
          role: msg.role === 'assistant' ? 'bot' as const : msg.role
        })).filter(msg => msg.role !== 'system'); // Exclude system messages from display

        // If we have messages from the server, replace our local state
        if (formattedMessages.length > 0) {
          setMessages(formattedMessages);
          setIsLoading(false); // Turn off loading if it was on
        }
      } catch (error) {
        // Error loading chat history
      }
    };

    loadChatHistory();
  }, [chatId, chatApi]);

  // Scroll to bottom when messages change
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim() || !chatId) return;

    const userMessage: Message = { role: 'user', content: input.trim() };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    // Show loading message immediately
    setMessages((prev) => [
      ...prev,
      { role: 'bot', content: 'Thinking...', isLoading: true }
    ]);

    try {
      const response = await chatApi.sendMessage(chatId, userMessage.content);

      // Format assistant message as bot for rendering
      const botMessage: Message = {
        ...response.response,
        role: 'bot'
      };

      // Replace the loading message with the actual response
      setMessages((prev) => prev.filter(msg => !msg.isLoading).concat([botMessage]));

      // Update chat in storage with the new last message
      updateChatLastMessage(chatId, userMessage.content);
    } catch (err) {
      // Replace loading message with error message
      setMessages((prev) =>
        prev.filter(msg => !msg.isLoading).concat([
          { role: 'bot', content: `Error: Unable to fetch response: ${err}` }
        ])
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!isLoading) {
      sendMessage();
    }
  };

  const toggleSources = (index: number) => {
    if (selectedMessageIndex === index) {
      setShowSources(false);
      setSelectedMessageIndex(null);
    } else {
      setShowSources(true);
      setSelectedMessageIndex(index);
    }
  };

  const renderSources = (sources: Source[]) => {
    return (
      <div className="mt-2 text-sm p-2 bg-base-300 rounded-md">
        <h4 className="font-bold mb-1">Sources:</h4>
        {sources.map((source, idx) => (
          <div key={idx} className="mb-2 p-2 bg-base-200 rounded">
            <div className="font-semibold">{source.title}</div>
            <div className="text-xs opacity-70">{source.content.substring(0, 150)}...</div>
            <div className="text-xs mt-1 flex gap-2">
              <span className="badge badge-sm">{source.category}</span>
              {source.relevance_score && (
                <span className="badge badge-sm badge-primary">Score: {source.relevance_score.toFixed(2)}</span>
              )}
            </div>
          </div>
        ))}
      </div>
    );
  };

  const renderMessageActions = (message: Message) => {
    if (message.role !== 'bot') return null;

    return (
      <div className="flex gap-2 mt-2">
        <button
          className="btn btn-sm btn-success"
          onClick={() => sendFeedback(message.id!, 'upvote')}
        >
          Upvote
        </button>
        <button
          className="btn btn-sm btn-error"
          onClick={() => sendFeedback(message.id!, 'downvote')}
        >
          Downvote
        </button>
        <button
          className="btn btn-sm btn-info"
          onClick={() => sendFeedback(message.id!, 'answered')}
        >
          This answered my question
        </button>
      </div>
    );
  };

  return (
    <div className="flex-1 flex flex-col h-full">
      <div className="flex-1 p-4 overflow-y-auto">
        {messages.length === 0 ? (
          <div className="h-full flex items-center justify-center text-gray-400">
            <p>No messages yet. Start a conversation!</p>
          </div>
        ) : (
          <div className="space-y-4 flex flex-col">
            {messages.map((message, index) => (
              <div
                key={index}
                className={`p-3 rounded ${
                  message.role === 'user'
                    ? 'bg-primary text-primary-content self-end'
                    : 'bg-base-200'
                } ${message.isLoading ? 'opacity-70' : ''}`}
                style={{ maxWidth: '80%', alignSelf: message.role === 'user' ? 'flex-end' : 'flex-start' }}
              >
                <div>
                  {message.isLoading ? (
                    <div className="flex items-center">
                      <span className="loading loading-dots loading-xs mr-2"></span>
                      {message.content}
                    </div>
                  ) : (
                    message.content
                  )}
                </div>

                {message.sources && message.sources.length > 0 && (
                  <>
                    <button
                      onClick={() => toggleSources(index)}
                      className="text-xs mt-2 underline"
                    >
                      {selectedMessageIndex === index && showSources ? 'Hide sources' : 'Show sources'}
                    </button>

                    {selectedMessageIndex === index && showSources && renderSources(message.sources)}
                  </>
                )}

                {renderMessageActions(message)}
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>
      <div className="p-4 bg-base-300">
        <form onSubmit={handleSubmit}>
          <div className="form-control">
            <div className="input-group flex">
              <input
                type="text"
                className="input flex-grow"
                placeholder="Type your message..."
                value={input}
                onChange={(e) => setInput(e.target.value)}
                disabled={isLoading}
              />
              <button
                type="submit"
                className="btn btn-primary"
                disabled={isLoading || !input.trim()}
              >
                {isLoading ?
                  <span className="loading loading-spinner"></span> :
                  'Send'
                }
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};

export default Chat;
