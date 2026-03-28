import { useEffect, useRef, useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import Layout from '../../components/Layout';
import { fetchMessages, sendMessage } from '../../api/api';
import { FiSend, FiRefreshCw } from 'react-icons/fi';

export default function TechnicianMessages() {
  const { user } = useAuth();
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [sending, setSending] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [statusMessage, setStatusMessage] = useState('');
  const messagesEndRef = useRef(null);

  useEffect(() => {
    loadMessages();
    const interval = setInterval(loadMessages, 10000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const loadMessages = async () => {
    setLoading(true);
    try {
      const data = await fetchMessages('technician', user?.username);
      setMessages(data);
      setError('');
    } catch (loadError) {
      setMessages([]);
      setError(loadError.message || 'Unable to load messages.');
    } finally {
      setLoading(false);
    }
  };

  const sortedMessages = [...messages].sort(
    (firstMessage, secondMessage) => new Date(firstMessage.timestamp) - new Date(secondMessage.timestamp)
  );

  const latestMessage = sortedMessages[sortedMessages.length - 1] || null;
  const replyTarget = latestMessage
    ? {
        receiverId:
          latestMessage.senderId === user?.id ? latestMessage.receiverId : latestMessage.senderId,
        name:
          latestMessage.senderId === user?.id ? latestMessage.receiverName : latestMessage.senderName,
        ticketId: latestMessage.ticketId,
        ticketAddress: latestMessage.ticketAddress,
      }
    : null;

  const handleSend = async () => {
    if (!newMessage.trim()) {
      return;
    }
    if (!replyTarget?.receiverId || !replyTarget?.ticketId) {
      setError('A linked supervisor conversation is required before you can reply here.');
      return;
    }

    try {
      setSending(true);
      const sentMessage = await sendMessage({
        receiverId: replyTarget.receiverId,
        ticketId: replyTarget.ticketId,
        text: newMessage,
      });
      setMessages((previousMessages) => [...previousMessages, sentMessage]);
      setNewMessage('');
      setError('');
      setStatusMessage(`Message sent to ${replyTarget.name}.`);
    } catch (sendError) {
      setError(sendError.message || 'Unable to send message.');
    } finally {
      setSending(false);
    }
  };

  return (
    <Layout>
      <div className="flex items-center justify-between mb-8">
        <h2 className="text-2xl font-semibold text-slate-800">Messages ({messages.length})</h2>
        <div className="flex gap-2">
          <button
            onClick={loadMessages}
            disabled={loading}
            className="p-2 text-slate-500 hover:text-slate-900 disabled:opacity-50"
          >
            <FiRefreshCw size={18} className={loading ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>

      {statusMessage && (
        <div className="mb-4 rounded-xl border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-900">
          {statusMessage}
        </div>
      )}
      {error && (
        <div className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          {error}
        </div>
      )}

      <div className="mb-4 rounded-2xl border border-slate-200 bg-slate-50 px-5 py-4 text-sm text-slate-700">
        {replyTarget ? (
          <>
            Replying to <span className="font-semibold">{replyTarget.name}</span> on ticket #
            <span className="font-semibold">{replyTarget.ticketId}</span>
            {replyTarget.ticketAddress ? `, ${replyTarget.ticketAddress}` : ''}.
          </>
        ) : (
          'Replies are enabled once a supervisor or support thread is linked to a ticket.'
        )}
      </div>

      <div className="mb-6 flex h-[60vh] flex-col overflow-hidden rounded-2xl border bg-white shadow-lg">
        <div className="flex-1 space-y-4 overflow-y-auto p-6">
          {loading ? (
            <div className="flex items-center justify-center py-12 text-slate-500">Loading messages...</div>
          ) : sortedMessages.length === 0 ? (
            <div className="py-16 text-center text-slate-500">
              <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-slate-100">
                Chat
              </div>
              <h3 className="mb-2 text-lg font-medium">No messages yet</h3>
              <p>Your ticket conversations will appear here.</p>
            </div>
          ) : (
            sortedMessages.map((message) => {
              const sentByCurrentUser = message.senderId === user?.id;
              const displayName = sentByCurrentUser ? 'You' : message.senderName;

              return (
                <div
                  key={message.id}
                  className={`flex gap-3 rounded-2xl p-4 ${
                    sentByCurrentUser
                      ? 'ml-auto max-w-md bg-blue-500 text-white'
                      : 'bg-slate-100 text-slate-900'
                  }`}
                >
                  <div
                    className={`flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full text-xs font-bold ${
                      sentByCurrentUser ? 'bg-blue-300' : 'bg-slate-300'
                    }`}
                  >
                    {displayName.slice(0, 2).toUpperCase()}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="mb-1 text-sm font-semibold">{displayName}</div>
                    <p className="break-words text-sm leading-relaxed">{message.text}</p>
                    <p className="mt-2 text-xs opacity-75">
                      {new Date(message.timestamp).toLocaleString()}
                    </p>
                  </div>
                </div>
              );
            })
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>

      <div className="rounded-2xl border bg-white p-6 shadow-lg">
        <div className="flex gap-3">
          <div className="relative flex-1">
            <textarea
              value={newMessage}
              onChange={(event) => setNewMessage(event.target.value)}
              placeholder="Type a message to the linked supervisor thread..."
              rows={2}
              className="w-full resize-none rounded-xl border border-slate-300 p-4 pr-12 focus:border-transparent focus:ring-2 focus:ring-blue-500"
              onKeyDown={(event) => {
                if (event.key === 'Enter' && event.ctrlKey) {
                  handleSend();
                }
              }}
            />
            <div className="absolute bottom-3 right-3 flex items-center gap-1 text-sm text-slate-400">
              Ctrl+Enter to send
            </div>
          </div>
          <button
            onClick={handleSend}
            disabled={sending || !newMessage.trim()}
            className="flex flex-shrink-0 items-center justify-center rounded-xl bg-gradient-to-r from-blue-500 to-indigo-600 p-4 text-white shadow-lg transition-all duration-200 hover:from-blue-600 hover:to-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <FiSend size={24} />
          </button>
        </div>
      </div>
    </Layout>
  );
}
