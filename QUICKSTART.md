# 🚀 QUICKSTART GUIDE - EDI X12 278 Processing Microservice

## ⚡ Super Quick Setup (1-2 minutes)

### Step 1: Run the Automated Setup
```bash
python quick_setup.py
```

This script will automatically:
- ✅ Check Python version
- ✅ Create .env configuration file  
- ✅ Guide you through API key setup
- ✅ Install all dependencies
- ✅ Create required directories
- ✅ Validate the system
- ✅ Show you how to launch

---

## 🔑 API Keys You Need

### Required: Groq API Key (FREE)
The AI features use Groq's lightning-fast inference engine.

**Get your FREE Groq API key:**
1. Go to: https://console.groq.com/
2. Sign up (free account)
3. Go to "API Keys" section
4. Create new API key
5. Copy the key (starts with `gsk_...`)

**Why Groq?**
- ⚡ **Lightning fast** - 750+ tokens/second
- 🆓 **Free tier** with generous limits
- 🧠 **Llama 3 70B** model for intelligent EDI analysis
- 🔧 **Easy integration** with our system

### Optional: OpenAI API Key
Alternative to Groq (paid service)
- Only needed if you prefer OpenAI over Groq
- Get from: https://platform.openai.com/

---

## 📁 What Gets Created

After running `quick_setup.py`, you'll have:

```
EDI X12 278/
├── .env                 # ✅ Your configuration file
├── uploads/             # ✅ File upload directory  
├── outputs/             # ✅ Processing results
├── temp/                # ✅ Temporary files
├── app/                 # ✅ Main application code
├── requirements.txt     # ✅ Dependencies list
├── sample_278.edi       # ✅ Test file ready to use
└── quick_setup.py       # ✅ Setup script you just ran
```

---

## 🚀 Launch the Application

### Option 1: Full System (Recommended)
Open **2 terminals** in your project directory:

**Terminal 1 - API Backend:**
```bash
python run_api.py
```

**Terminal 2 - Web Interface:**  
```bash
python run_streamlit.py
```

**Access Points:**
- 🎨 **Web Interface**: http://localhost:8501
- 📚 **API Docs**: http://localhost:8000/docs
- ❤️ **Health Check**: http://localhost:8000/health

### Option 2: API Only
```bash
python run_api.py
```
Then visit: http://localhost:8000/docs

### Option 3: Development Mode
```bash
# Terminal 1 - API with auto-reload
uvicorn app.api.main:app --reload --port 8000

# Terminal 2 - Streamlit with auto-reload  
streamlit run streamlit_app.py --server.port 8501
```

---

## 🧪 Test the System

### 1. Quick Web Test
1. Go to http://localhost:8501
2. Click "Upload & Process" 
3. Upload the included `sample_278.edi` file
4. Enable "AI Analysis" ✅
5. Choose "FHIR" output format
6. Click "Process File"
7. View the magic! 🎉

### 2. Quick API Test
```bash
# Test with sample file
curl -X POST "http://localhost:8000/upload" \
  -F "file=@sample_278.edi" \
  -F "enable_ai_analysis=true" \
  -F "output_format=fhir"

# Test validation only
curl -X POST "http://localhost:8000/validate" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "ISA*00*          *00*          *ZZ*SENDER         *ZZ*RECEIVER       *230815*1430*U*00501*000000001*0*P*>~\nGS*HS*SENDER*RECEIVER*20230815*1430*000000001*X*005010X217~\nST*278*000000001~",
    "enable_ai_analysis": true
  }'
```

---

## 🔧 Configuration

### Your .env file contains:
```bash
# API Keys
GROQ_API_KEY=your_groq_api_key_here    # Add your Groq key here

# Server Settings  
API_PORT=8000                          # API server port
STREAMLIT_PORT=8501                    # Web interface port

# File Processing
MAX_FILE_SIZE=52428800                 # 50MB max file size
VALIDATE_SEGMENTS=true                 # Enable segment validation
STRICT_VALIDATION=false                # Relaxed validation mode

# AI Settings
AI_MODEL=llama3-70b-8192              # Groq's fastest model
```

### To add your API key:
Edit `.env` file and replace:
```
GROQ_API_KEY=your_groq_api_key_here
```
with:
```
GROQ_API_KEY=gsk_your_actual_key_here
```

---

## ✨ What You Get

### 🔍 EDI Validation
- **Structural validation** against X12 standards
- **TR3 compliance** checking for healthcare 
- **Element-level validation** with detailed errors
- **Control number verification**

### 🤖 AI-Powered Analysis  
- **Anomaly detection** using Llama 3 70B
- **Pattern analysis** for data quality insights
- **Smart suggestions** for fixing issues
- **Risk assessment** (low/medium/high)
- **Confidence scoring** for reliability

### 🔄 FHIR Mapping
- **CoverageEligibilityRequest** for X12 278 (prior auth)
- **Patient, Practitioner, Organization** resources
- **Coverage** information mapping
- **Bundle** creation for complete transactions
- **Reverse mapping** FHIR back to EDI

### 📊 Web Interface Features
- **Drag & drop** file upload
- **Real-time processing** with progress
- **Interactive validation** results
- **AI insights** dashboard  
- **FHIR resource** visualization
- **Download results** in multiple formats
- **Job history** and monitoring
- **Processing statistics**

---

## 🆘 Troubleshooting

### Common Issues

**1. "ModuleNotFoundError: No module named 'pyx12'"**
```bash
pip install -r requirements.txt
```

**2. "AI analysis disabled"**
- Add your Groq API key to `.env` file
- Restart the services

**3. "Port already in use"**
- Change ports in `.env` file:
```
API_PORT=8001
STREAMLIT_PORT=8502
```

**4. "Failed to parse EDI file"**
- Check EDI file format
- Use the included `sample_278.edi` for testing
- Ensure file encoding is UTF-8

**5. "Connection refused"**
- Make sure API backend is running first
- Check if ports are available
- Verify firewall settings

### Get Help
- 📖 **API Documentation**: http://localhost:8000/docs
- 🔍 **Check logs** in the terminal output
- 📋 **Run validation**: `python setup_and_validate.py`
- ❤️ **Health check**: http://localhost:8000/health

---

## 🎯 Next Steps

1. **Test with your own EDI files**
2. **Explore the API endpoints** at `/docs`
3. **Set up production environment** with proper secrets
4. **Enable additional AI models** (OpenAI)
5. **Customize FHIR mappings** for your use case
6. **Scale with Docker** for production deployment

---

## 🎉 Congratulations!

You now have a fully functional EDI X12 278 processing system with:
- ⚡ **Lightning-fast parsing** with pyx12
- 🧠 **AI-powered validation** with Groq/Llama 3
- 🔄 **Modern FHIR mapping** for interoperability  
- 🎨 **Beautiful web interface** with Streamlit
- 📚 **Enterprise API** with FastAPI
- 🔒 **Production-ready** architecture

**Enjoy processing your EDI files with AI superpowers!** 🚀 