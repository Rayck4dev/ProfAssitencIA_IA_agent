using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Microsoft.VisualBasic;
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

        private LessonPlanService _lessonPlanService;
        private AppDbContext _appDbContext;

        

        public LessonPlanController(LessonPlanService lessonPlanService, AppDbContext appDbContext)
        {
            _lessonPlanService = lessonPlanService;
            _appDbContext = appDbContext;
        }

        [HttpPost]
        public async Task<IActionResult> GenerateLessonPlan([FromBody] ApiRequestResp request)
        {
            
            if (string.IsNullOrWhiteSpace(request.message))
            {
                return  BadRequest("Mensagem vazia");
            }
            int conversationId = 0;
            if(request.conversation_id == null)
            {
                Conversation newConversation = new Conversation();

                newConversation.InstallationId = request.installation_id;
                
                _appDbContext.Conversations.Add(newConversation);
                newConversation.Title = "Nova conversa";
                await _appDbContext.SaveChangesAsync();

                conversationId = newConversation.Id;

                MessageEntity newMessage = new MessageEntity();

                newMessage.ConversationId = newConversation.Id;
                newMessage.Role = "user";
                newMessage.Content = request.message;
                Console.WriteLine(newConversation.Title);
                _appDbContext.MessageEntities.Add(newMessage);

                await _appDbContext.SaveChangesAsync();
            }
            List<Message> historico = new List<Message>();

            if (request.conversation_id != null)
            {
                string conversationIdString = request.conversation_id;

                if (int.TryParse(conversationIdString, out int resultado))
                {
                    Conversation? conversation = _appDbContext.Conversations
                        .FirstOrDefault(c => c.Id == resultado);

                    if (conversation == null)
                    {
                        return NotFound("Conversa nao encontrada");
                    }

                    List<MessageEntity> mensagens = _appDbContext.MessageEntities
                        .Where(c => c.ConversationId == conversation.Id)
                        .ToList();

                    foreach (MessageEntity mensagem in mensagens)
                    {
                        Message novaMensagem = new Message();

                        novaMensagem.Role = mensagem.Role;
                        novaMensagem.Content = mensagem.Content;

                        historico.Add(novaMensagem);
                    }

                    MessageEntity newChat = new MessageEntity();

                    newChat.ConversationId = conversation.Id;
                    newChat.Role = "user";
                    newChat.Content = request.message;

                    _appDbContext.MessageEntities.Add(newChat);

                    await _appDbContext.SaveChangesAsync();
                    conversationId = conversation.Id;
                }
                else
                {
                    return BadRequest("Erro de conversao");
                }
            }

            LessonPlanResult resultadoIA = await _lessonPlanService.ProfMessage(request.message, historico);

            MessageEntity respostaIA = new MessageEntity();

            respostaIA.ConversationId = conversationId;
            respostaIA.Role = "assistant";
            respostaIA.Content = resultadoIA.Response;

            _appDbContext.MessageEntities.Add(respostaIA);

            await _appDbContext.SaveChangesAsync();
            resultadoIA.ConversationId = conversationId.ToString();
            return Ok(resultadoIA);
        }

    } 
}
