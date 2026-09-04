namespace ProfAssistenc.Api.Entities
{
    public class Conversation
    {
        public int Id { get; set; }
        public string? Title { get; set; }
        public string InstallationId { get; set; }
        public DateTime UpdatedAt { get; set; }
        public List<MessageEntity> Messages { get; set; }
    }
}
