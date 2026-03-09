# 🚀 Push Your Code to GitHub

Quick guide to get your Gro-Sential AI project on GitHub.

---

## Step 1: Create Repository on GitHub (2 minutes)

1. **Go to GitHub**: https://github.com/Kotlasuhasreddy123
2. **Click "New"** (green button) or go to: https://github.com/new
3. **Fill in details**:
   - Repository name: `Gro-Sential-AI`
   - Description: `AI-Powered Food Waste Reduction Platform using AWS Bedrock, DynamoDB, and Rekognition`
   - Visibility: **Public** (to showcase your work)
   - ❌ Don't initialize with README (you already have one)
   - ❌ Don't add .gitignore (you already have one)
   - ❌ Don't add license (you already have one)
4. **Click "Create repository"**

---

## Step 2: Push Your Code (3 minutes)

Open PowerShell in your project folder and run:

```bash
# Navigate to your project
cd "C:\Users\suhas\Desktop\Project Grosential\Grosential_backend"

# Initialize git (if not already done)
git init

# Add all files
git add .

# Commit with a message
git commit -m "Initial commit - Gro-Sential AI Food Waste Platform"

# Add your GitHub repository as remote
git remote add origin https://github.com/Kotlasuhasreddy123/Gro-Sential-AI.git

# Push to GitHub
git branch -M main
git push -u origin main
```

**If you get an authentication error**, you'll need to:
1. Generate a Personal Access Token (PAT) on GitHub
2. Go to: https://github.com/settings/tokens
3. Click "Generate new token (classic)"
4. Select scopes: `repo` (all)
5. Copy the token
6. Use it as your password when pushing

---

## Step 3: Verify Upload (1 minute)

1. Go to: https://github.com/Kotlasuhasreddy123/Gro-Sential-AI
2. You should see all your files:
   - ✅ README.md
   - ✅ LICENSE
   - ✅ server.py
   - ✅ index.html
   - ✅ And all other files

---

## Step 4: Add Topics/Tags (1 minute)

Make your repository discoverable:

1. On your repository page, click the ⚙️ gear icon next to "About"
2. Add topics:
   - `aws`
   - `aws-bedrock`
   - `aws-rekognition`
   - `dynamodb`
   - `ai`
   - `machine-learning`
   - `food-waste`
   - `python`
   - `flask`
   - `claude-ai`
3. Click "Save changes"

---

## Step 5: Deploy to Render.com (5 minutes)

Now that your code is on GitHub, deploy it for free:

1. **Go to**: https://render.com
2. **Sign up** with your GitHub account
3. **Click "New +"** → "Web Service"
4. **Connect GitHub** → Select `Gro-Sential-AI` repository
5. **Configure**:
   ```
   Name: gro-sential-ai
   Region: Oregon (US West)
   Branch: main
   Runtime: Python 3
   Build Command: pip install -r requirements.txt
   Start Command: gunicorn server:app --bind 0.0.0.0:$PORT
   ```
6. **Add Environment Variables**:
   - Click "Advanced" → "Add Environment Variable"
   - Add:
     ```
     AWS_ACCESS_KEY_ID = your_access_key
     AWS_SECRET_ACCESS_KEY = your_secret_key
     AWS_DEFAULT_REGION = us-east-2
     ```
7. **Select Free Plan**
8. **Click "Create Web Service"**

Wait 5-10 minutes for deployment. Your app will be live at:
`https://gro-sential-ai.onrender.com`

---

## Step 6: Update README with Live URL (1 minute)

Once deployed, update your README:

```bash
# Edit README.md and add at the top:
# 🌐 **Live Demo**: https://gro-sential-ai.onrender.com

# Commit and push
git add README.md
git commit -m "Add live demo URL"
git push
```

---

## Step 7: Share Your Project (5 minutes)

### LinkedIn Post

```
🚀 Excited to share my latest project: Gro-Sential AI!

An AI-powered platform that reduces food waste using AWS services:

🤖 AWS Bedrock (Claude AI) for intelligent recommendations
📸 AWS Rekognition for food detection
💾 DynamoDB for scalable storage
🤝 Smart trading system for food exchange
👨‍🍳 AI recipe generation

🔗 Live Demo: https://gro-sential-ai.onrender.com
💻 GitHub: https://github.com/Kotlasuhasreddy123/Gro-Sential-AI

Built with Python, Flask, and AWS. Open source under MIT License!

#AWS #AI #MachineLearning #FoodWaste #Python #CloudComputing #BuildInPublic
```

### Twitter/X Post

```
Built an AI-powered food waste reduction platform! 🥗

✨ Features:
- AI food detection
- Smart expiry alerts  
- Trading system
- Recipe generation

🔧 Tech: @awscloud Bedrock, Rekognition, DynamoDB

🔗 https://gro-sential-ai.onrender.com
💻 https://github.com/Kotlasuhasreddy123/Gro-Sential-AI

#AWS #AI #BuildInPublic
```

---

## Troubleshooting

### "Permission denied" error when pushing?

**Solution**: Set up SSH key or use Personal Access Token

**Option 1: Use HTTPS with Token**
```bash
# When prompted for password, use your Personal Access Token
# Generate at: https://github.com/settings/tokens
```

**Option 2: Use SSH**
```bash
# Generate SSH key
ssh-keygen -t ed25519 -C "suhasreddykotla@lewisu.edu"

# Add to GitHub: https://github.com/settings/keys
# Change remote to SSH
git remote set-url origin git@github.com:Kotlasuhasreddy123/Gro-Sential-AI.git
```

### Files not showing up on GitHub?

**Check .gitignore**:
```bash
# View what's being ignored
git status

# If important files are ignored, edit .gitignore
# Then add and commit again
```

### Render deployment failing?

**Check logs**:
1. Render dashboard → Your service → Logs
2. Common issues:
   - Missing dependencies in requirements.txt
   - Wrong start command
   - Missing environment variables

---

## Next Steps

- [ ] Code pushed to GitHub ✓
- [ ] Repository is public ✓
- [ ] Topics added ✓
- [ ] Deployed to Render.com
- [ ] Live URL added to README
- [ ] Shared on LinkedIn
- [ ] Shared on Twitter
- [ ] Submit to AWS Builders

---

## Your Repository

**URL**: https://github.com/Kotlasuhasreddy123/Gro-Sential-AI

**Profile**: https://github.com/Kotlasuhasreddy123

---

**Ready to push? Run the commands in Step 2!** 🚀
