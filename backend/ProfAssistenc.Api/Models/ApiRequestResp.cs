namespace ProfAssistenc.Api.Models
{
    public class ApiRequestResp
    {
        public string installation_id { get; set; }
        public string? conversation_id { get; set; }
        public required string message { get; set; }
        public List<Message> messages { get; set; }
    }
}
