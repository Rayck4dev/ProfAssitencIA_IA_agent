using ProfAssistenc.Api.Models;
using System.Text;
using System.Text.Json;

namespace ProfAssistenc.Api.Services
{
    public class AIService
    {
        private HttpClient _httpClient;
        private IConfiguration _configuration;
        public AIService(HttpClient httpClient, IConfiguration configuration)
        {
            _httpClient = httpClient;
            _configuration = configuration;
        }
        public async Task<string> GenerateResponse(List<Message> history)
        {
            List<GeminiContent> contents = new List<GeminiContent>();
            foreach (Message message in history)
            {
                GeminiContent newGContent = new GeminiContent();

                newGContent.Role = message.Role == "assistant" ? "model" : "user";          
                Part newPart = new Part();

                newPart.text = message.Content;
                List<Part> lPart = new List<Part>();
                lPart.Add(newPart);

                newGContent.Parts = lPart;

                contents.Add(newGContent);
            }
            var payload = new
            {
                contents = contents
            };

            var options = new JsonSerializerOptions
            {
                PropertyNamingPolicy = JsonNamingPolicy.CamelCase
            };
            string jsonString = JsonSerializer.Serialize(payload, options);
            var url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent";
            var content = new StringContent(jsonString, Encoding.UTF8, "application/json");
            var apiKey = _configuration.GetSection("Gemini:ApiKey").Value;
            try
            {
                var request = new HttpRequestMessage(HttpMethod.Post, url);
                request.Headers.Add("x-goog-api-key", apiKey);
                request.Content = content;
                HttpResponseMessage httpResponse = await _httpClient.SendAsync(request); 
                Console.WriteLine(jsonString);

                string responseBody = await httpResponse.Content.ReadAsStringAsync();
                if (!httpResponse.IsSuccessStatusCode)
                {
                    return $"Erro do Gemini: {httpResponse.StatusCode} - {responseBody}";
                }

                Console.WriteLine("RESPOSTA DO GEMINI:");
                Console.WriteLine(responseBody);

                var gResponse = JsonSerializer.Deserialize<GeminiResponse>(responseBody, options);
                Console.WriteLine(gResponse == null);
                Console.WriteLine(gResponse?.Candidates == null);

                var firstCandidate = gResponse.Candidates.FirstOrDefault();
                var candidateContent = firstCandidate.content;
                var parts = candidateContent.parts;
                var firstParts = parts.FirstOrDefault();
                string textPart = firstParts.text;
                Console.WriteLine(httpResponse);
                Console.WriteLine(responseBody);
                return textPart;

            }
            catch(HttpRequestException e)
            {
                Console.WriteLine(e.Message);
                return $"Erro na requisicao {e.Message}";
            }
        }
    }
}