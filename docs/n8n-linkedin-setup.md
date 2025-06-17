# LinkedIn Backfill n8n Workflow Setup

## 🚀 Overview
This workflow scrapes LinkedIn posts from founder profiles going back to 2023-01-01 and stores them in Supabase with `embedding = NULL` for later processing.

## 🔧 Prerequisites

### 1. n8n Cloud Setup
- Sign up at [n8n.cloud](https://n8n.cloud/)
- Create a new workflow

### 2. Required Credentials
- **LinkedIn Account**: Valid login credentials
- **Supabase Database**: Connection details from your Supabase project

## 📋 Step-by-Step Setup

### Step 1: Import Workflow
1. In n8n, click **"Import from File"**
2. Upload `workflows/linkedin_backfill.json`
3. The workflow will appear with 5 connected nodes

### Step 2: Configure Environment Variables
In n8n Settings → Environment Variables:
```
LINKEDIN_EMAIL=your-linkedin-email@company.com
LINKEDIN_PASSWORD=your-linkedin-password
```

### Step 3: Set Up Supabase Credentials
1. Click the **"Insert to Supabase"** node
2. Create new PostgreSQL credentials:
   - **Host**: `db.your-project-ref.supabase.co`
   - **Database**: `postgres`
   - **User**: `postgres`
   - **Password**: Your Supabase database password
   - **Port**: `5432`
   - **SSL**: `require`

### Step 4: Configure Founder URLs
Edit the **"Founder URLs"** node:
```json
[
  "https://linkedin.com/in/actual-founder-1",
  "https://linkedin.com/in/actual-founder-2",
  "https://linkedin.com/in/actual-founder-3"
]
```

### Step 5: Install Puppeteer (if needed)
n8n Cloud should have Puppeteer available, but if running self-hosted:
```bash
npm install puppeteer
```

## 🔄 Workflow Flow

```
Manual Trigger → Set Variables → Founder URLs → LinkedIn Scraper → Supabase Insert
```

### Node Details:

1. **Manual Trigger**: Start the workflow manually
2. **Set Variables**: Sets `start_date = "2023-01-01"`
3. **Founder URLs**: List of LinkedIn profile URLs to scrape
4. **LinkedIn Scraper**: 
   - Logs into LinkedIn with Puppeteer
   - Scrolls through each founder's activity
   - Extracts post text, URL, and timestamp
   - Stops when reaching start_date
5. **Supabase Insert**: Bulk inserts posts with `embedding = NULL`

## ⚠️ Important Notes

### LinkedIn Rate Limiting
- The workflow includes delays to avoid being blocked
- Uses `page.waitForNetworkIdle()` for proper loading
- Headless mode can be enabled for production

### Data Mapping
The scraper needs to map LinkedIn URLs to `founder_id` from your database:
```sql
-- You'll need to populate the founders table first
INSERT INTO founders (full_name, linkedin_url) VALUES 
('Founder Name', 'https://linkedin.com/in/founder-profile');
```

### Error Handling
- Browser closes automatically on errors
- Failed posts are logged but don't stop the workflow
- Consider adding retry logic for production use

## 🧪 Testing

### Test with Single Founder
1. Modify "Founder URLs" to include just one profile
2. Set start_date to recent date (e.g., "2024-06-01")
3. Run workflow manually
4. Check Supabase for inserted posts

### Verification Query
```sql
SELECT COUNT(*), founder_id 
FROM linkedin_posts 
WHERE embedding IS NULL 
GROUP BY founder_id;
```

## 🔄 Production Considerations

### Scheduling
- Set up cron trigger for regular backfills
- Consider daily/weekly runs for new posts

### Security
- Use n8n's credential management
- Never hardcode passwords in workflow

### Scaling
- Process founders in batches
- Add error handling and notifications
- Consider proxy rotation for large-scale scraping

## 🛠️ Troubleshooting

### Common Issues:
1. **Login Failed**: Check LinkedIn credentials
2. **Selector Not Found**: LinkedIn may have changed their HTML structure
3. **Database Connection**: Verify Supabase credentials and whitelist n8n IPs
4. **Rate Limiting**: Increase delays between requests

### Debug Mode:
- Enable n8n's debug mode
- Check browser console logs
- Monitor network requests in Puppeteer 