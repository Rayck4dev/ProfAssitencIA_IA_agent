using ProfAssistenc.Api.Models;
using System.Text;
using System.Text.Json;

namespace ProfAssistenc.Api.Services
{
    public class AIService
    {
        private HttpClient _httpClient;
        private IConfiguration _configuration;
        private string _url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent";
        private JsonSerializerOptions _options = new JsonSerializerOptions
        {
            PropertyNamingPolicy = JsonNamingPolicy.CamelCase
        };
        private string? _apiKey;
        public AIService(HttpClient httpClient, IConfiguration configuration)
        {
            _httpClient = httpClient;
            _configuration = configuration;
            _apiKey = _configuration.GetSection("Gemini:ApiKey").Value;
        }
        
        public async Task<string?> GenerateResponse(List<Message> history)
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

            string jsonString = JsonSerializer.Serialize(payload, _options);
            try
            {
                for (int tentativa = 1; tentativa <= 3; tentativa++)
                {
                    var request = new HttpRequestMessage(HttpMethod.Post, _url);
                    request.Headers.Add("x-goog-api-key", _apiKey);
                    request.Content = new StringContent(jsonString, Encoding.UTF8, "application/json");

                    HttpResponseMessage httpResponse = await _httpClient.SendAsync(request);
                    string responseBody = await httpResponse.Content.ReadAsStringAsync();

                    if (httpResponse.IsSuccessStatusCode)
                        return ExtractResponseText(responseBody);

                    if ((int)httpResponse.StatusCode == 503)
                    {
                        await Task.Delay(1000 * tentativa);
                        continue;
                    }

                    Console.WriteLine($"Erro Gemini: {(int)httpResponse.StatusCode}");
                    Console.WriteLine(responseBody);

                    return null;

                }

                return null;
            }
            catch (HttpRequestException e)
            {
                Console.WriteLine(e.Message);
                return null;
            }
        }
        public async Task<string?> GenerateTitle(Message message)
        {
            GeminiContent content = new GeminiContent();
            content.Role = "user";

            Part newPart = new Part();
            newPart.text = $"Gere um título curto e objetivo para esta conversa com base na mensagem do usuário. Retorne apenas o título, sem explicações e com no máximo 8 palavras. {message.Content}";
            List<Part> lPart = new List<Part>();
            lPart.Add(newPart);
            content.Parts = lPart;

            List<GeminiContent> gmList = new List<GeminiContent>();
            gmList.Add(content);
            var payload = new
            {
                contents = gmList
            };

            string jsonString = JsonSerializer.Serialize(payload, _options);
            try
            {
                for (int tentativa = 1; tentativa <= 3; tentativa++)
                {
                    var request = new HttpRequestMessage(HttpMethod.Post, _url);
                    request.Headers.Add("x-goog-api-key", _apiKey);
                    request.Content = new StringContent(jsonString, Encoding.UTF8, "application/json");

                    HttpResponseMessage httpResponse = await _httpClient.SendAsync(request);
                    string responseBody = await httpResponse.Content.ReadAsStringAsync();

                    if (httpResponse.IsSuccessStatusCode)
                    {
                        string? title = ExtractResponseText(responseBody);
                        Console.WriteLine($"Título gerado pela IA: {title}");
                        return title;
                    }

                    if ((int)httpResponse.StatusCode == 503)
                    {
                        await Task.Delay(1000 * tentativa);
                        continue;
                    }
                    Console.WriteLine($"Erro Gemini ao gerar título: {(int)httpResponse.StatusCode}");
                    Console.WriteLine(responseBody);

                    return null;

                }
                Console.WriteLine("Não foi possível gerar o título após 3 tentativas.");
                return null;
            }
            catch (HttpRequestException e)
            {
                Console.WriteLine(e.Message);
                return null;
            }

        }
        private string? ExtractResponseText(string responseBody)
        {
            try
            {
                var gResponse = JsonSerializer.Deserialize<GeminiResponse>(responseBody, _options);

                if (gResponse == null || gResponse.Candidates == null) return null;
                var firstCandidate = gResponse.Candidates.FirstOrDefault();
                if (firstCandidate == null) return null;
                var candidateContent = firstCandidate.content;
                var parts = candidateContent.parts;
                var firstParts = parts.FirstOrDefault();
                if (firstParts == null) return null;
                if (string.IsNullOrWhiteSpace(firstParts.text)) return null;
                string textPart = firstParts.text;
                return textPart;
            }
            catch(JsonException e)
            {
                Console.WriteLine(e.Message);
                return null;
            }
            
        }
    }
}