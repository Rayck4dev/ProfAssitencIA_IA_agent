using Microsoft.AspNetCore.Mvc;
using ProfAssistenc.Api.Data;
using ProfAssistenc.Api.Entities;
using ProfAssistenc.Api.Models;
using ProfAssistenc.Api.Services;

namespace ProfAssistenc.Api.Controllers
{
    [Route("api/[controller]")]
    [ApiController]
    public class LessonPlanController : ControllerBase
    {
        private readonly LessonPlanService _lessonPlanService;

        private readonly AppDbContext _appDbContext;

        private readonly AIService _aiService;

        private readonly ConversationService _conversationService;

        public LessonPlanController(LessonPlanService lessonPlanService, AppDbContext appDbContext, AIService aiService, ConversationService conversationService)
        {
            _lessonPlanService = lessonPlanService;
            _appDbContext = appDbContext;
            _aiService = aiService;
            _conversationService = conversationService;
        }

        [HttpPost]
        public async Task<IActionResult> GenerateLessonPlan([FromBody] ApiRequestResp request)
        {
            
            if (string.IsNullOrWhiteSpace(request.message))
            {
                return  BadRequest("Mensagem vazia");
            }
            int conversationId = 0;
           
            List<Message> history = new List<Message>();

            if (request.conversation_id != null)
            {
                string conversationIdString = request.conversation_id;

                if (int.TryParse(conversationIdString, out int parsedConversationId))
                {
                    Conversation? conversation = await _conversationService.GetConversationById(
                        parsedConversationId,
                        request.installation_id
                    );

                    if (conversation == null)
                    {
                        return NotFound("Conversa nao encontrada");
                    }

                    history = await _conversationService.GetConversationHistory(conversation.Id);
                    conversationId = conversation.Id;
                    await _conversationService.AddUserMessage(conversationId, request.message);
                }
                else
                {
                    return BadRequest("Erro de conversao");
                }
            }

            LessonPlanResult aiResult = await _lessonPlanService.ProfMessage(request.message, history);
            if (aiResult.Response == null) return StatusCode(502, "Não foi possível obter uma resposta da IA.");
            if (request.conversation_id == null)
            {
                Conversation newConversation = new Conversation();

                newConversation.InstallationId = request.installation_id;
                newConversation.UpdatedAt = DateTime.UtcNow;
                _appDbContext.Conversations.Add(newConversation);
                newConversation.Title = "Nova conversa";
                await _appDbContext.SaveChangesAsync();

                conversationId = newConversation.Id;

                await _conversationService.AddUserMessage(conversationId, request.message );

                Message firstMessage = new Message();
                firstMessage.Role = "user";
                firstMessage.Content = request.message;

                string? title = await _aiService.GenerateTitle(firstMessage);
                if (title != null)
                {
                    newConversation.Title = title;
                    await _appDbContext.SaveChangesAsync();
                }

            }
            MessageEntity aiMessage = new MessageEntity();

            aiMessage.ConversationId = conversationId;
            aiMessage.Role = "assistant";
            aiMessage.Content = aiResult.Response;

            _appDbContext.MessageEntities.Add(aiMessage);

            await _appDbContext.SaveChangesAsync();
            aiResult.ConversationId = conversationId.ToString();
            return Ok(aiResult);
        }

    } 
}
