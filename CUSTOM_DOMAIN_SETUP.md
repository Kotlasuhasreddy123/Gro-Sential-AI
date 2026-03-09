# Custom Domain Setup Guide for Grosential

Transform your AWS URL into a professional custom domain: `https://gro-sential.com`

**Current URL**: http://grosential-env.eba-epdixgxd.us-east-2.elasticbeanstalk.com/
**Target URL**: https://gro-sential.com

---

## Step 1: Purchase Your Domain (15 minutes)

⚠️ **AWS Free Tier Note**: Domain registration is NOT included in AWS Free Tier. You must pay for the domain.

### Option A: AWS Route 53 (Recommended - Everything in one place)

1. Go to AWS Console → Route 53 → Domains → Register Domain
2. Search for `gro-sential.com`
3. Add to cart and complete purchase (~$12/year)
4. Auto-creates hosted zone for you
5. Wait for registration (can take 10 minutes to 3 hours)

**Cost**: $12/year (NOT free tier eligible)

### Option B: External Registrar (Namecheap, GoDaddy, etc.) - CHEAPER

1. Go to [Namecheap.com](https://www.namecheap.com) or [GoDaddy.com](https://www.godaddy.com)
2. Search for `gro-sential.com`
3. Purchase domain (~$8-10/year with first-year discount)
4. Keep the registrar tab open - you'll need it later

**Cost**: $8-10/year (NOT free tier eligible)

### Option C: FREE Alternative - Use Freenom (Free for 12 months)

⚠️ **Limited TLDs**: Only .tk, .ml, .ga, .cf, .gq domains are free

1. Go to [Freenom.com](https://www.freenom.com)
2. Search for `gro-sential.tk` or `gro-sential.ml`
3. Select "Get it now" → Checkout (Free for 12 months)
4. Create account and complete registration

**Cost**: FREE for 12 months ✓ (then renew or switch)

**Recommendation**: If budget allows, buy .com domain ($10-12/year). If testing only, use Freenom free domain.

---

## Step 2: Set Up Route 53 Hosted Zone (5 minutes)

⚠️ **AWS Free Tier**: Route 53 hosted zone costs $0.50/month (NOT included in free tier)

**Alternative FREE Option**: Use Cloudflare DNS (see Option B below)

### Option A: AWS Route 53 (Recommended for AWS integration)

**If you bought via Route 53**: Skip to Step 3 (already done)

**If you bought via external registrar**:

1. AWS Console → Route 53 → Hosted zones → Create hosted zone
2. Enter domain name: `gro-sential.com`
3. Type: Public hosted zone
4. Click "Create hosted zone"
5. **IMPORTANT**: Note the 4 nameservers (look like):
   ```
   ns-1234.awsdns-12.org
   ns-5678.awsdns-56.com
   ns-9012.awsdns-90.net
   ns-3456.awsdns-34.co.uk
   ```

6. Go back to your domain registrar (Namecheap/GoDaddy/Freenom)
7. Find "Nameservers" or "DNS Settings"
8. Change from default to "Custom DNS"
9. Enter all 4 AWS nameservers
10. Save changes
11. **Wait 5-48 hours for DNS propagation** (usually 1-2 hours)

**Cost**: $0.50/month ($6/year)

### Option B: Cloudflare DNS (100% FREE Alternative)

If you want to avoid Route 53 costs:

1. Go to [Cloudflare.com](https://www.cloudflare.com) → Sign up (FREE)
2. Add site → Enter `gro-sential.com`
3. Select FREE plan
4. Cloudflare scans your DNS records
5. Note Cloudflare nameservers (like):
   ```
   ava.ns.cloudflare.com
   bob.ns.cloudflare.com
   ```
6. Go to your domain registrar
7. Change nameservers to Cloudflare's nameservers
8. Wait for activation (5 minutes - 24 hours)
9. In Cloudflare DNS settings, add A record:
   - Type: A
   - Name: @
   - Content: Get IP from `ping grosential-env.eba-epdixgxd.us-east-2.elasticbeanstalk.com`
   - Proxy status: DNS only (grey cloud)
10. Add CNAME for www:
    - Type: CNAME
    - Name: www
    - Content: gro-sential.com

**Cost**: FREE ✓ (includes free SSL too!)

**Note**: If using Cloudflare, skip Route 53 steps and use Cloudflare for DNS management.

---

## Step 3: Request SSL Certificate (10 minutes)

✅ **AWS Free Tier**: SSL certificates via AWS Certificate Manager (ACM) are 100% FREE forever!

You need HTTPS for security and trust.

### Option A: AWS Certificate Manager (FREE - Recommended)

1. AWS Console → Certificate Manager (ACM)
2. **IMPORTANT**: Switch region to `us-east-2` (Ohio) - same as your Elastic Beanstalk
3. Click "Request certificate"
4. Choose "Request a public certificate"
5. Add domain names:
   - `gro-sential.com`
   - `www.gro-sential.com`
6. Validation method: **DNS validation** (easier with Route 53)
7. Click "Request"

**If using Route 53**:
8. Click "Create records in Route 53" (blue button)
9. Confirm
10. Wait 5-30 minutes for validation (status changes to "Issued")

**If using Cloudflare DNS**:
8. Copy the CNAME name and value shown in ACM
9. Go to Cloudflare → DNS → Add record
10. Type: CNAME
11. Paste the name (remove domain part, e.g., `_abc123.gro-sential.com` → `_abc123`)
12. Paste the value
13. Proxy status: DNS only (grey cloud)
14. Save
15. Wait 5-30 minutes for validation

**Check status**: Refresh the certificate page until it shows "Issued" ✓

**Cost**: FREE ✓ (AWS Free Tier - always free)

### Option B: Let's Encrypt via Cloudflare (FREE Alternative)

If using Cloudflare DNS, you can use Cloudflare's free SSL:

1. Cloudflare dashboard → SSL/TLS
2. Set SSL mode to "Full (strict)"
3. Origin Server → Create Certificate
4. Generate certificate (valid for 15 years)
5. Copy certificate and private key
6. Add to your application configuration

**Cost**: FREE ✓

**Recommendation**: Use AWS ACM (Option A) - it's free and integrates seamlessly with Elastic Beanstalk.

---

## Step 4: Configure Elastic Beanstalk for HTTPS (10 minutes)

### Method A: AWS Console (Easier)

1. Go to Elastic Beanstalk → Environments → `grosential-env`
2. Left sidebar → Configuration
3. Find "Load balancer" category → Click "Edit"
4. Scroll to "Listeners" section
5. Click "Add listener":
   - Port: `443`
   - Protocol: `HTTPS`
   - SSL certificate: Select your certificate from dropdown
   - SSL policy: Keep default
6. Click "Add"
7. Scroll down → Click "Apply"
8. Wait 3-5 minutes for environment update

### Method B: AWS CLI (Faster if you know CLI)

```bash
# Get your certificate ARN
aws acm list-certificates --region us-east-2

# Note the CertificateArn, then:
aws elasticbeanstalk update-environment \
  --environment-name grosential-env \
  --option-settings \
    Namespace=aws:elbv2:listener:443,OptionName=Protocol,Value=HTTPS \
    Namespace=aws:elbv2:listener:443,OptionName=SSLCertificateArns,Value=arn:aws:acm:us-east-2:ACCOUNT:certificate/CERT-ID
```

---

## Step 5: Create DNS Records in Route 53 (5 minutes)

Now point your domain to Elastic Beanstalk.

1. AWS Console → Route 53 → Hosted zones
2. Click on `gro-sential.com`
3. Click "Create record"

### Record 1: Root domain (gro-sential.com)

- Record name: *leave blank*
- Record type: `A - Routes traffic to an IPv4 address`
- Toggle "Alias" to ON
- Route traffic to: 
  - Choose "Alias to Elastic Beanstalk environment"
  - Region: `US East (Ohio) us-east-2`
  - Environment: Select `grosential-env.eba-epdixgxd.us-east-2.elasticbeanstalk.com`
- Routing policy: Simple routing
- Click "Create records"

### Record 2: WWW subdomain (www.gro-sential.com)

- Click "Create record" again
- Record name: `www`
- Record type: `A - Routes traffic to an IPv4 address`
- Toggle "Alias" to ON
- Route traffic to:
  - Choose "Alias to Elastic Beanstalk environment"
  - Region: `US East (Ohio) us-east-2`
  - Environment: Select `grosential-env.eba-epdixgxd.us-east-2.elasticbeanstalk.com`
- Click "Create records"

---

## Step 6: Force HTTPS Redirect (5 minutes)

Make sure all HTTP traffic redirects to HTTPS.

### Option A: Elastic Beanstalk Configuration File

1. Create file `.ebextensions/https-redirect.config` in your project:

```yaml
option_settings:
  aws:elbv2:listener:80:
    ListenerEnabled: 'true'
    Protocol: HTTP
    Rules: redirect-to-https

Resources:
  AWSEBV2LoadBalancerListenerRule:
    Type: AWS::ElasticLoadBalancingV2::ListenerRule
    Properties:
      Actions:
        - Type: redirect
          RedirectConfig:
            Protocol: HTTPS
            Port: '443'
            StatusCode: HTTP_301
      Conditions:
        - Field: path-pattern
          Values:
            - '*'
      ListenerArn:
        Ref: AWSEBV2LoadBalancerListener
      Priority: 1
```

2. Deploy:
```bash
eb deploy
```

### Option B: Application-Level Redirect (Simpler)

Add to your `server.py` before any routes:

```python
@app.before_request
def redirect_to_https():
    if request.headers.get('X-Forwarded-Proto') == 'http':
        url = request.url.replace('http://', 'https://', 1)
        return redirect(url, code=301)
```

Then redeploy:
```bash
eb deploy
```

---

## Step 7: Test Your Domain (2 minutes)

Wait 5-10 minutes after completing all steps, then test:

1. Open browser (incognito mode recommended)
2. Try these URLs:
   - http://gro-sential.com → Should redirect to https://gro-sential.com
   - https://gro-sential.com → Should work ✓
   - http://www.gro-sential.com → Should redirect to https://www.gro-sential.com
   - https://www.gro-sential.com → Should work ✓

3. Check SSL certificate:
   - Click padlock icon in browser
   - Should show "Connection is secure"
   - Certificate should be valid

---

## Troubleshooting

### Domain not working after 2 hours?

**Check DNS propagation**:
```bash
# Check if DNS is propagated
nslookup gro-sential.com

# Or use online tool
# Visit: https://www.whatsmydns.net/#A/gro-sential.com
```

**Check nameservers**:
```bash
dig gro-sential.com NS
```
Should show AWS nameservers.

### SSL Certificate stuck on "Pending validation"?

1. Go to Certificate Manager
2. Click on your certificate
3. Check if CNAME records were created in Route 53
4. If not, manually create them (details shown in certificate page)

### "502 Bad Gateway" error?

1. Check Elastic Beanstalk environment health (should be green)
2. Check if HTTPS listener was added correctly
3. Verify certificate is in "Issued" status

### HTTP works but HTTPS doesn't?

1. Verify HTTPS listener (port 443) is configured
2. Check SSL certificate is attached to listener
3. Verify certificate region matches Elastic Beanstalk region (us-east-2)

### "Your connection is not private" warning?

1. Certificate might still be validating (wait 30 minutes)
2. Check certificate covers both `gro-sential.com` and `www.gro-sential.com`
3. Clear browser cache and try again

---

## Cost Breakdown

### Standard Setup (AWS Route 53)
- Domain registration (.com): $10-15/year (NOT free tier)
- Route 53 hosted zone: $0.50/month = $6/year (NOT free tier)
- SSL certificate (ACM): **FREE** ✓ (Always free)
- Elastic Beanstalk: Already paying for it
- **Total additional cost**: ~$16-21/year

### Budget Setup (Cloudflare DNS)
- Domain registration (.com): $8-10/year (NOT free tier)
- Cloudflare DNS: **FREE** ✓
- Cloudflare SSL: **FREE** ✓
- Elastic Beanstalk: Already paying for it
- **Total additional cost**: ~$8-10/year

### Free Tier Maximum Savings (Freenom + Cloudflare)
- Domain registration (.tk/.ml): **FREE** for 12 months ✓
- Cloudflare DNS: **FREE** ✓
- Cloudflare SSL: **FREE** ✓
- Elastic Beanstalk: Already paying for it
- **Total additional cost**: $0/year (first year)

### AWS Free Tier Eligible Services
✅ **Always FREE**:
- AWS Certificate Manager (ACM) - SSL certificates
- First 1 million Route 53 queries/month
- Elastic Beanstalk service itself (you pay for underlying resources)

❌ **NOT Free Tier**:
- Domain registration ($8-15/year)
- Route 53 hosted zone ($0.50/month)
- Elastic Beanstalk EC2 instances (free tier: 750 hours/month t2.micro for 12 months)
- DynamoDB (free tier: 25 GB storage, 25 read/write capacity units)

### Recommended Setup for Students/Budget
1. Use Freenom for free domain (12 months)
2. Use Cloudflare for free DNS
3. Use AWS ACM for free SSL
4. Keep Elastic Beanstalk on t2.micro (free tier eligible for 12 months)
5. **Total cost**: $0 for first year ✓

---

## Quick Reference Commands

```bash
# Check DNS propagation
nslookup gro-sential.com

# Check nameservers
dig gro-sential.com NS

# Test HTTPS
curl -I https://gro-sential.com

# List certificates
aws acm list-certificates --region us-east-2

# Check Elastic Beanstalk status
eb status

# Redeploy application
eb deploy
```

---

## Timeline Summary

- Domain purchase: 10 min - 3 hours
- DNS propagation: 5 min - 48 hours (usually 1-2 hours)
- SSL validation: 5-30 minutes
- Elastic Beanstalk update: 3-5 minutes
- **Total time**: 1-2 hours (if everything goes smoothly)

---

## Next Steps After Domain is Live

1. Update all documentation with new URL
2. Add domain to AWS Builders article
3. Update social media links
4. Set up Google Analytics with new domain
5. Submit to search engines (Google Search Console)
6. Update any API endpoints or webhooks

---

## Support Resources

- AWS Route 53 Documentation: https://docs.aws.amazon.com/route53/
- AWS Certificate Manager: https://docs.aws.amazon.com/acm/
- Elastic Beanstalk Custom Domains: https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/customdomains.html
- DNS Checker: https://www.whatsmydns.net/

---

**Your application is ready for a professional domain! 🚀**
