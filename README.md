# 🥗 Gro-Sential AI - AI-Powered Food Waste Reduction Platform

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![AWS](https://img.shields.io/badge/AWS-Bedrock%20%7C%20DynamoDB-orange.svg)](https://aws.amazon.com/)

> **Reducing food waste through AI-powered inventory management, intelligent trading, and recipe generation**

Created by **Suhas Reddy Kotla** | [GitHub](https://github.com/Kotlasuhasreddy123) | [LinkedIn](https://www.linkedin.com/in/suhasreddykotla) | [Email](mailto:suhasreddykotla@lewisu.edu)

---

## 🌟 Overview

Gro-Sential AI is a comprehensive food waste reduction platform that leverages AWS AI services to help users:

- 📸 **Scan & Track** - Use AI image recognition to automatically identify and catalog food items
- ⏰ **Smart Alerts** - Get AI-powered notifications before food expires
- 🤝 **Trade Items** - Exchange surplus food with nearby users through an intelligent matching system
- 👨‍🍳 **Recipe Generation** - Get personalized recipes based on your available ingredients
- 💬 **AI Chatbot** - Ask questions about food storage, recipes, and nutrition

---

## 🎯 Key Features

### 1. AI-Powered Food Detection
- Upload photos of groceries
- AWS Rekognition automatically identifies items
- Extracts expiry dates from packaging
- Estimates market value

### 2. Intelligent Expiry Alerts
- AWS Bedrock (Claude 3 Haiku) analyzes your inventory
- Sends personalized alerts for items nearing expiration
- Suggests optimal usage strategies

### 3. Smart Trading System
- List items you want to trade
- Browse available items from other users
- Negotiate trades with counter-offers
- Real-time trade status updates

### 4. AI Recipe Generator
- Input available ingredients
- Get creative, personalized recipes
- Includes cooking instructions and nutritional info
- Optimized to use expiring items first

### 5. Intelligent Chatbot
- Ask about food storage tips
- Get recipe suggestions
- Learn about nutrition
- Powered by AWS Bedrock

---

## 🏗️ Architecture

```
┌─────────────────┐
│   Frontend      │
│  (HTML/JS/CSS)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Flask Backend  │
│   (Python)      │
└────────┬────────┘
         │
    ┌────┴────┬──────────┬──────────┐
    ▼         ▼          ▼          ▼
┌────────┐ ┌──────┐ ┌─────────┐ ┌──────┐
│DynamoDB│ │Bedrock│ │Rekognition│ │ IAM │
└────────┘ └──────┘ └─────────┘ └──────┘
```

### Tech Stack

**Backend:**
- Python 3.9+ with Flask
- Boto3 (AWS SDK)
- AWS DynamoDB (NoSQL database)
- AWS Bedrock (Claude 3 Haiku for AI)
- AWS Rekognition (Image analysis)

**Frontend:**
- Vanilla JavaScript
- HTML5/CSS3
- Responsive design

**Deployment:**
- AWS Elastic Beanstalk
- AWS Route 53 (DNS)
- AWS Certificate Manager (SSL)

---

## 🚀 Quick Start

### Prerequisites

- Python 3.9 or higher
- AWS Account with credentials configured
- AWS CLI installed
- Git

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/Kotlasuhasreddy123/Gro-Sential-AI.git
cd Gro-Sential-AI
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure AWS credentials**
```bash
aws configure
# Enter your AWS Access Key ID
# Enter your AWS Secret Access Key
# Region: us-east-2
# Output format: json
```

4. **Create DynamoDB tables**
```bash
python create_tables.py
```

5. **Run locally**
```bash
python server.py
```

6. **Open browser**
```
http://localhost:5000
```

---

## 📦 Deployment

### Deploy to AWS Elastic Beanstalk

```bash
# Install EB CLI
pip install awsebcli

# Initialize
eb init -p python-3.9 grosential-app --region us-east-2

# Create environment
eb create grosential-env

# Deploy
eb deploy

# Open in browser
eb open
```

### Deploy to Heroku (Free Alternative)

```bash
# Install Heroku CLI
# Visit: https://devcenter.heroku.com/articles/heroku-cli

# Login
heroku login

# Create app
heroku create grosential-app

# Set environment variables
heroku config:set AWS_ACCESS_KEY_ID=your_key
heroku config:set AWS_SECRET_ACCESS_KEY=your_secret
heroku config:set AWS_DEFAULT_REGION=us-east-2

# Deploy
git push heroku main

# Open
heroku open
```

### Deploy to Render (Free Alternative)

1. Go to [Render.com](https://render.com)
2. Connect your GitHub repository
3. Create new Web Service
4. Set environment variables (AWS credentials)
5. Deploy automatically

---

## 🔑 Environment Variables

Create a `.env` file (not included in repo):

```env
AWS_ACCESS_KEY_ID=your_access_key_id
AWS_SECRET_ACCESS_KEY=your_secret_access_key
AWS_DEFAULT_REGION=us-east-2
FLASK_SECRET_KEY=your_random_secret_key
```

---

## 📊 Database Schema

### Users Table
- Email (Primary Key)
- Name
- Password (hashed)
- Location
- CreatedAt

### Inventory Table
- ItemID (Primary Key)
- UserEmail
- ItemName
- Quantity
- ExpiryDate
- MarketValue
- ImageURL
- AddedDate

### Trades Table
- TradeID (Primary Key)
- RequesterEmail
- ProviderEmail
- RequestedItems
- OfferedItems
- Status
- CounterOffer
- CreatedAt

---

## 🎨 Screenshots

### Dashboard
![Dashboard](screenshots/dashboard.png)

### Food Detection
![Food Detection](screenshots/food-detection.png)

### Trading System
![Trading](screenshots/trading.png)

### Recipe Generator
![Recipes](screenshots/recipes.png)

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

**Important Notes:**
- The code is open source under MIT License
- The "Grosential" name and branding are trademarked by Suhas Reddy Kotla
- If you fork this project, please rebrand it with your own name
- Attribution is required (see LICENSE file)

---

## 🏆 Awards & Recognition

- AWS Builders Program Featured Project
- [Add your awards here]

---

## 📧 Contact

**Suhas Reddy Kotla**
- Email: suhasreddykotla@lewisu.edu
- LinkedIn: [linkedin.com/in/suhasreddykotla](https://www.linkedin.com/in/suhasreddykotla)
- GitHub: [@Kotlasuhasreddy123](https://github.com/Kotlasuhasreddy123)

---

## 🙏 Acknowledgments

- AWS for providing cloud infrastructure and AI services
- Claude (Anthropic) for powering the intelligent features
- Lewis University for academic support
- Open source community for inspiration

---

## 📈 Project Stats

![GitHub stars](https://img.shields.io/github/stars/Kotlasuhasreddy123/Gro-Sential-AI?style=social)
![GitHub forks](https://img.shields.io/github/forks/Kotlasuhasreddy123/Gro-Sential-AI?style=social)
![GitHub watchers](https://img.shields.io/github/watchers/Kotlasuhasreddy123/Gro-Sential-AI?style=social)

---

## 🗺️ Roadmap

- [ ] Mobile app (React Native)
- [ ] Multi-language support
- [ ] Community features (forums, groups)
- [ ] Gamification (points, badges)
- [ ] Integration with grocery stores
- [ ] Blockchain-based trade verification
- [ ] Carbon footprint tracking

---

**Made with ❤️ by Suhas Reddy Kotla**

*Reducing food waste, one meal at a time.*
