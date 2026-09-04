using Microsoft.EntityFrameworkCore;
using ProfAssistenc.Api.Entities;

namespace ProfAssistenc.Api.Data
{
    public class AppDbContext : DbContext
    {
        public AppDbContext(DbContextOptions<AppDbContext> options): base(options)
        {

        }
        public DbSet<Conversation> Conversations { get; set; }
        public DbSet<MessageEntity> MessageEntities { get; set;  }
    }
}
