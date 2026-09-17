using ProfAssistenc.Api.Models;

namespace ProfAssistenc.Api.Services
{
    public class LessonPlanService
    {
        private AIService _aiService;

        public LessonPlanService(AIService aIService)
        {
            _aiService = aIService;
        }
        public async Task<LessonPlanResult> ProfMessage(string message, List<Message> history)
        {
           Message mensagem = new Message();
           mensagem.Role = "user";
           mensagem.Content = message;
           history.Add(mensagem);

            LessonPlanResult result = new LessonPlanResult();

            Console.WriteLine($"Quantidade de mensagens: {history.Count}");

            foreach (Message item in history)
            {
                Console.WriteLine($"Role: {item.Role}");
                Console.WriteLine($"Content: {item.Content}");
                Console.WriteLine("----------------------");
            }

           string? aiReturn = await _aiService.GenerateResponse(history);
           result.Response = aiReturn;
           return result;
        }
        
    }
}
