using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using ProfAssistenc.Api.Data;
using ProfAssistenc.Api.Entities;
using ProfAssistenc.Api.Models;

namespace ProfAssistenc.Api.Controllers
{
    [Route("api/[controller]")]
    [ApiController]
    public class ConversationsController : ControllerBase
    {
        private AppDbContext _appDbContext;
        public ConversationsController(AppDbContext appDbContext)
        {
            _appDbContext = appDbContext;
        }
        [HttpGet]
        public async Task<IActionResult> GetConversations(string installation_id)
        {
            var installationConversations = await _appDbContext.Conversations
                .Where(c => c.InstallationId == installation_id)
                .ToListAsync();
            return Ok( new { conversations = installationConversations});
        }
        [HttpGet("{id}")]
        public async Task<IActionResult> GetConversationById(int id, string installation_id)
        {
            Conversation? conversation = await _appDbContext.Conversations
                .Where(c => c.InstallationId == installation_id)
                .Include(c => c.Messages)
                .FirstOrDefaultAsync(c => c.Id == id);
            if (conversation == null)
            {
                return NotFound("Conversa nao encontrada");
            }
            return Ok(conversation);
        }
        [HttpPatch("{id}")]
        public async Task<IActionResult> UpdateConversationTitle(int id, UpdateConversationRequest request)
        {
            var conversation = await _appDbContext.Conversations
                .Where(c => c.InstallationId == request.installation_id)
                .FirstOrDefaultAsync(c => c.Id == id);
            if (conversation == null)
            {
                return NotFound("Conversa nao encontrada");
            }
            conversation.Title = request.Title;
            conversation.UpdatedAt = DateTime.UtcNow;
            await _appDbContext.SaveChangesAsync();
            return Ok(conversation);
        }
        [HttpDelete("{id}")]
        public async Task<IActionResult> DeleteConversationById(int id, string installation_id)
        {
            Conversation? conversation = await _appDbContext.Conversations
           .Where(c => c.InstallationId == installation_id)
           .FirstOrDefaultAsync(c => c.Id == id);
            if (conversation == null) { return NotFound("Conversa nao encontrada"); }
            _appDbContext.Conversations.Remove(conversation);
            await _appDbContext.SaveChangesAsync();
            return Ok(conversation);
        }
    }
}
