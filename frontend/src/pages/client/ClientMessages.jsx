import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import Layout from '../../components/Layout';
import { FiSend, FiPhone, FiMapPin } from 'react-icons/fi';
import { fetchMessages, sendMessage } from '../../api/api';

const formatConversationFromMessage = (message, currentUserId) => {
  const sentByCurrentUser = message.senderId === currentUserId;
  const partnerId = sentByCurrentUser ? message.receiverId : message.senderId;
  const partnerName = sentByCurrentUser ? message.receiverName : message.senderName;
  const partnerPhone = sentByCurrentUser ? message.receiverPhone : message.senderPhone;
  const conversationKey = `${partnerId || 'unknown'}:${message.ticketId || 'no-ticket'}`;

  return {
    key: conversationKey,
    partnerId,
    name: partnerName || 'Support Team',
    phone: partnerPhone || '',
    ticketId: message.ticketId,
    ticketAddress: message.ticketAddress || '',
    ticketLatitude: message.ticketLatitude,
    ticketLongitude: message.ticketLongitude,
    lastMessage: message.text,
    timestamp: message.timestamp,
    avatar: `https://ui-avatars.com/api/?name=${encodeURIComponent(partnerName || 'Support')}&background=0D8ABC&color=fff`,
  };
};

export default function ClientMessages() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [messages, setMessages] = useState([]);
  const [selectedConversation, setSelectedConversation] = useState(null);
  const [newMessage, setNewMessage] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [statusMessage, setStatusMessage] = useState('');

  const getConversations = (messageList) => {
    const conversationMap = {};

    messageList.forEach((message) => {
      const conversation = formatConversationFromMessage(message, user?.id);
      const existingConversation = conversationMap[conversation.key];
      if (!existingConversation || new Date(conversation.timestamp) > new Date(existingConversation.timestamp)) {
        conversationMap[conversation.key] = conversation;
      }
    });

    return Object.values(conversationMap).sort(
      (firstConversation, secondConversation) =>
        new Date(secondConversation.timestamp) - new Date(firstConversation.timestamp)
    );
  };

  useEffect(() => {
    if (user) {
      loadMessages();
    }
  }, [user]);

  const loadMessages = async () => {
    setLoading(true);
    try {
      const data = await fetchMessages('client', user?.username);
      const conversations = getConversations(data);
      setMessages(data);
      setSelectedConversation((previousConversation) =>
        conversations.find((conversation) => conversation.key === previousConversation?.key) ||
        conversations[0] ||
        null
      );
      setError('');
    } catch (loadError) {
      setMessages([]);
      setSelectedConversation(null);
      setError(loadError.message || 'Unable to load messages.');
    } finally {
      setLoading(false);
    }
  };

  const conversations = getConversations(messages);
  const activeConversation =
    conversations.find((conversation) => conversation.key === selectedConversation?.key) ||
    selectedConversation ||
    conversations[0] ||
    null;

  const selectedConvMessages = messages
    .filter((message) => {
      const conversation = formatConversationFromMessage(message, user?.id);
      return conversation.key === activeConversation?.key;
    })
    .sort((firstMessage, secondMessage) => new Date(firstMessage.timestamp) - new Date(secondMessage.timestamp));

  const handleSendMessage = async () => {
    if (!newMessage.trim() || !activeConversation) {
      return;
    }

    try {
      const sentMessage = await sendMessage({
        text: newMessage,
        receiverId: activeConversation.partnerId,
        ticketId: activeConversation.ticketId,
      });
      setMessages((previousMessages) => [...previousMessages, sentMessage]);
      setNewMessage('');
      setError('');
      setStatusMessage(`Message sent to ${activeConversation.name}.`);
    } catch (sendError) {
      setError(sendError.message || 'Unable to send message.');
    }
  };

  const handleCallConversation = () => {
    if (!activeConversation?.phone) {
      setStatusMessage('No phone number is available for this conversation yet.');
      return;
    }

    window.location.href = `tel:${activeConversation.phone}`;
  };

  const handleOpenLocation = () => {
    if (!activeConversation?.ticketId) {
      setStatusMessage('This conversation is not linked to a service ticket yet.');
      return;
    }

    navigate(`/client/requests/${activeConversation.ticketId}`);
  };

  return (
    <Layout>
      <div className="min-h-screen bg-slate-50 p-4">
        <div className="max-w-6xl mx-auto">
          <div className="mb-6">
            <h1 className="text-3xl font-bold text-slate-900">Messages</h1>
            <p className="text-slate-600 mt-1">
              Communicate with support team and technicians assigned to your requests
            </p>
          </div>

          {statusMessage && (
            <div className="mb-4 rounded-lg border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-900">
              {statusMessage}
            </div>
          )}
          {error && (
            <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
              {error}
            </div>
          )}

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3 h-[600px]">
            <div className="bg-white rounded-lg shadow-sm border border-slate-200 overflow-hidden flex flex-col">
              <div className="p-4 border-b border-slate-200">
                <h2 className="font-semibold text-slate-900">Conversations</h2>
              </div>
              <div className="flex-1 overflow-y-auto">
                {loading ? (
                  <div className="p-4 text-center text-slate-500">Loading conversations...</div>
                ) : conversations.length === 0 ? (
                  <div className="p-4 text-center text-slate-500">No conversations yet</div>
                ) : (
                  conversations.map((conversation) => (
                    <button
                      key={conversation.key}
                      onClick={() => setSelectedConversation(conversation)}
                      className={`w-full border-b border-slate-100 p-3 text-left transition-colors hover:bg-slate-50 ${
                        activeConversation?.key === conversation.key ? 'bg-blue-50' : ''
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <img
                          src={conversation.avatar}
                          alt={conversation.name}
                          className="h-10 w-10 rounded-full"
                        />
                        <div className="min-w-0 flex-1">
                          <p className="truncate font-medium text-slate-900">{conversation.name}</p>
                          <p className="truncate text-sm text-slate-600">{conversation.lastMessage}</p>
                          {conversation.ticketAddress && (
                            <p className="truncate text-xs text-slate-400">{conversation.ticketAddress}</p>
                          )}
                        </div>
                      </div>
                    </button>
                  ))
                )}
              </div>
            </div>

            <div className="lg:col-span-2 bg-white rounded-lg shadow-sm border border-slate-200 flex flex-col">
              {activeConversation ? (
                <>
                  <div className="flex items-center justify-between border-b border-slate-200 p-4">
                    <div className="flex items-center gap-3">
                      <img
                        src={activeConversation.avatar}
                        alt={activeConversation.name}
                        className="h-10 w-10 rounded-full"
                      />
                      <div>
                        <h3 className="font-semibold text-slate-900">{activeConversation.name}</h3>
                        <p className="text-xs text-slate-500">
                          {activeConversation.ticketAddress || 'Linked to your current service ticket'}
                        </p>
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={handleCallConversation}
                        className="rounded-lg p-2 text-slate-600 transition-colors hover:bg-slate-100"
                      >
                        <FiPhone size={18} />
                      </button>
                      <button
                        type="button"
                        onClick={handleOpenLocation}
                        className="rounded-lg p-2 text-slate-600 transition-colors hover:bg-slate-100"
                      >
                        <FiMapPin size={18} />
                      </button>
                    </div>
                  </div>

                  <div className="flex-1 overflow-y-auto bg-slate-50 p-4 space-y-4">
                    {selectedConvMessages.length === 0 ? (
                      <div className="py-8 text-center text-slate-500">Start a conversation</div>
                    ) : (
                      selectedConvMessages.map((message) => {
                        const sentByCurrentUser = message.senderId === user?.id;
                        return (
                          <div
                            key={message.id}
                            className={`flex ${sentByCurrentUser ? 'justify-end' : 'justify-start'}`}
                          >
                            <div
                              className={`max-w-xs rounded-lg px-4 py-2 ${
                                sentByCurrentUser
                                  ? 'bg-blue-500 text-white'
                                  : 'border border-slate-200 bg-white'
                              }`}
                            >
                              <p className="text-sm">{message.text}</p>
                              <p
                                className={`mt-1 text-xs ${
                                  sentByCurrentUser ? 'opacity-75' : 'text-slate-500'
                                }`}
                              >
                                {new Date(message.timestamp).toLocaleTimeString()}
                              </p>
                            </div>
                          </div>
                        );
                      })
                    )}
                  </div>

                  <div className="border-t border-slate-200 p-4">
                    <div className="flex gap-2">
                      <input
                        type="text"
                        value={newMessage}
                        onChange={(event) => setNewMessage(event.target.value)}
                        onKeyDown={(event) => event.key === 'Enter' && handleSendMessage()}
                        placeholder="Type your message..."
                        className="flex-1 rounded-lg border border-slate-300 px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                      <button
                        onClick={handleSendMessage}
                        disabled={!newMessage.trim()}
                        className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-white transition-colors hover:bg-blue-700 disabled:opacity-50"
                      >
                        <FiSend size={18} />
                      </button>
                    </div>
                  </div>
                </>
              ) : (
                <div className="flex flex-1 items-center justify-center text-slate-500">
                  Select a conversation to start messaging
                </div>
              )}
            </div>
          </div>

          <div className="mt-6 rounded-lg border border-blue-200 bg-blue-50 p-4">
            <p className="text-sm text-blue-900">
              Keep all service-related discussion tied to the correct ticket so your technician and support team
              can follow the full history in one place.
            </p>
          </div>
        </div>
      </div>
    </Layout>
  );
}
