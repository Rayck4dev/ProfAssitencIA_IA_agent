using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Microsoft.VisualBasic;
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
        public async Task<IActionResult> GenerateConversations(string installation_id)
        {
            var installationConversations = await _appDbContext.Conversations.Where(c => c.InstallationId == installation_id).ToListAsync();
            return Ok(installationConversations);
        }
        [HttpGet("{id}")]
        public async Task<IActionResult> GetConversationById(int id)
        {
            Conversation? conversation = _appDbContext.Conversations
                .Include(c => c.Messages)
                .FirstOrDefault(c => c.Id == id);
            if (conversation == null)
            {
                return NotFound("Conversa nao encontrada");
            }
            return Ok(conversation);
        }
        [HttpPatch("{id}")]
        public async Task<IActionResult> UpdateConversationTitle(int id, UpdateConversationRequest request)
        {
            var titleConversation = await _appDbContext.Conversations
                .FirstOrDefaultAsync(c => c.Id == id);
            if (titleConversation == null)
            {
                return NotFound("Conversa nao encontrada");
            }
            titleConversation.Title = request.Title;
            await _appDbContext.SaveChangesAsync();
            return Ok(titleConversation);
        }
    }
}
