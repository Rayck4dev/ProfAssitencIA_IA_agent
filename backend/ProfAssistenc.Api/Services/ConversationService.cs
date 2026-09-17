using Microsoft.EntityFrameworkCore;
using ProfAssistenc.Api.Data;
using ProfAssistenc.Api.Entities;
using ProfAssistenc.Api.Models;

namespace ProfAssistenc.Api.Services
{
    public class ConversationService
    {
        private AppDbContext _appDbContext;

        public ConversationService(AppDbContext appDbContext)
        {
            _appDbContext = appDbContext;
        }

        public async Task<List<Message>> GetConversationHistory(int conversationId)
        {
            List<Message> finalMessage = new List<Message>();

            List<MessageEntity> messages = await _appDbContext.MessageEntities
            .Where(c => c.ConversationId == conversationId)
            .ToListAsync();

            foreach (MessageEntity message in messages)
            {
                Message historyMessage = new Message();

                historyMessage.Role = message.Role;
                historyMessage.Content = message.Content;

                finalMessage.Add(historyMessage);

            }
            return finalMessage;
        }

        public async Task<Conversation?> GetConversationById(int conversationId, string installationId)
        {
            Conversation? conversation = await _appDbContext.Conversations
            .FirstOrDefaultAsync(c => c.Id == conversationId &&
                              c.InstallationId == installationId);
            return conversation;
        }

        public async Task<MessageEntity?> AddUserMessage(int conversationId, string message)
        {
            MessageEntity newMessage = new MessageEntity();
            Conversation? conversation = await _appDbContext.Conversations
            .FirstOrDefaultAsync(c => c.Id == conversationId);
            if (conversation == null) return null;
            newMessage.ConversationId = conversationId;
            newMessage.Role = "user";
            newMessage.Content = message;
            conversation.UpdatedAt = DateTime.UtcNow;

            _appDbContext.MessageEntities.Add(newMessage);
            await _appDbContext.SaveChangesAsync();
            return newMessage;
        }
    }
}