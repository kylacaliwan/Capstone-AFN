import { api, getApiErrorMessage } from './core';

const normalizeMessage = (message) => ({
  ...message,
  text: message.text || message.message_text || '',
  timestamp: message.timestamp || message.created_at,
  senderId: message.sender,
  senderName: message.sender_name || String(message.sender || ''),
  senderPhone: message.sender_phone || '',
  receiverId: message.receiver,
  receiverName: message.receiver_name || String(message.receiver || ''),
  receiverPhone: message.receiver_phone || '',
  ticketId: message.ticket_id || message.ticket || null,
  ticketAddress: message.ticket_address || '',
  ticketLatitude: message.ticket_latitude == null ? null : Number(message.ticket_latitude),
  ticketLongitude: message.ticket_longitude == null ? null : Number(message.ticket_longitude),
});

export const fetchMessages = async (role, username) => {
  try {
    const { data } = await api.get('/messages/', { params: { role, username } });
    const messageArray = Array.isArray(data) ? data : (Array.isArray(data?.results) ? data.results : []);
    return Array.isArray(messageArray) ? messageArray.map(normalizeMessage) : [];
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Unable to load messages.'));
  }
};

export const sendMessage = async (messageData) => {
  try {
    const payload = {
      receiver: messageData.receiverId ?? messageData.receiver,
      ticket: messageData.ticketId ?? messageData.ticket,
      text: messageData.text ?? messageData.message_text,
    };

    if (!payload.receiver) {
      throw new Error('A message receiver is required.');
    }
    if (!payload.ticket) {
      throw new Error('A related ticket is required to send a message.');
    }
    if (!payload.text || !String(payload.text).trim()) {
      throw new Error('Message text is required.');
    }

    const { data } = await api.post('/messages/', payload);
    return normalizeMessage(data);
  } catch (error) {
    if (error instanceof Error && !error.response) {
      throw error;
    }
    throw new Error(getApiErrorMessage(error, 'Unable to send message.'));
  }
};

export const fetchNotifications = async () => {
  try {
    const { data } = await api.get('/notifications/');
    const notifArray = Array.isArray(data) ? data : (Array.isArray(data?.results) ? data.results : []);
    return Array.isArray(notifArray) ? notifArray : [];
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Unable to load notifications.'));
  }
};

export const markNotificationAsRead = async (notificationId) => {
  try {
    const { data } = await api.post(`/notifications/${notificationId}/mark_read/`);
    return data;
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Unable to mark notification as read.'));
  }
};

export const markAllNotificationsAsRead = async () => {
  try {
    const { data } = await api.post('/notifications/mark_all_read/');
    return data;
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Unable to mark all notifications as read.'));
  }
};

export const getUnreadNotificationCount = async () => {
  try {
    const { data } = await api.get('/notifications/unread_count/');
    return data.unread_count || 0;
  } catch (error) {
    throw new Error(getApiErrorMessage(error, 'Unable to load unread notification count.'));
  }
};
