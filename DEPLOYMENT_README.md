# EDI X12 278 Processor - Deployment Guide
## Complete Streamlit-Based Application

---

## 🚀 Quick Start Deployment

### Option 1: Direct Streamlit Deployment (Recommended)

```bash
# 1. Install dependencies
pip install -r requirements_deploy.txt

# 2. Set up environment variables
export GROQ_API_KEY="your_groq_api_key_here"

# 3. Run the application
streamlit run streamlit_deploy.py
```

**Access your app at:** `http://localhost:8501`

### Option 2: Docker Deployment

```bash
# 1. Build and run with Docker Compose
docker-compose up --build

# 2. Access at http://localhost:8501
```

### Option 3: Cloud Deployment (Streamlit Cloud)

1. Push your code to GitHub
2. Connect to [Streamlit Cloud](https://streamlit.io/cloud)
3. Deploy directly from your repository
4. Add `GROQ_API_KEY` in Streamlit Cloud secrets

---

## 📋 Prerequisites

### System Requirements
- **Python**: 3.9+ (3.11 recommended)
- **Memory**: 2GB+ RAM
- **Storage**: 1GB+ free space
- **Network**: Internet access for AI features

### Required Environment Variables
```bash
# Essential
GROQ_API_KEY=your_groq_api_key_here

# Optional
LOG_LEVEL=INFO
DEBUG=false
MAX_FILE_SIZE=52428800  # 50MB
```

---

## 🛠️ Deployment Options

### 1. Local Development Deployment

Perfect for testing and development:

```bash
# Clone or copy your files
cd edi-x12-278-processor

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements_deploy.txt

# Set environment variables
echo "GROQ_API_KEY=your_actual_key_here" > .env

# Run application
streamlit run streamlit_deploy.py --server.port 8501
```

### 2. Production Server Deployment

For production environments:

```bash
# Install system-wide (with proper user)
sudo -u appuser pip install -r requirements_deploy.txt

# Set up systemd service (Linux)
sudo cp edi-processor.service /etc/systemd/system/
sudo systemctl enable edi-processor
sudo systemctl start edi-processor

# Or use PM2 (Node.js process manager)
pm2 start ecosystem.config.js
```

### 3. Docker Container Deployment

Containerized deployment with Docker:

```bash
# Build the image
docker build -t edi-processor:latest .

# Run with environment variables
docker run -d \
  --name edi-processor \
  -p 8501:8501 \
  -e GROQ_API_KEY=your_key_here \
  -v $(pwd)/uploads:/app/uploads \
  -v $(pwd)/outputs:/app/outputs \
  edi-processor:latest

# Or use Docker Compose
docker-compose up -d
```

### 4. Cloud Platform Deployment

#### Streamlit Cloud (Easiest)
1. Push code to GitHub repository
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repo
4. Set secrets in advanced settings:
   ```
   GROQ_API_KEY = "your_groq_api_key_here"
   ```
5. Deploy!

#### Heroku Deployment
```bash
# Install Heroku CLI and login
heroku login

# Create app
heroku create your-edi-processor

# Set environment variables
heroku config:set GROQ_API_KEY=your_key_here

# Deploy
git push heroku main
```

#### AWS EC2 Deployment
```bash
# Launch EC2 instance (t3.medium recommended)
# Connect via SSH

# Install dependencies
sudo apt update
sudo apt install python3 python3-pip nginx

# Clone your app
git clone your-repo-url
cd edi-x12-278-processor

# Set up virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements_deploy.txt

# Configure nginx (optional)
sudo cp nginx.conf /etc/nginx/sites-available/edi-processor
sudo ln -s /etc/nginx/sites-available/edi-processor /etc/nginx/sites-enabled/
sudo systemctl restart nginx

# Run with screen or tmux
screen -S edi-app
streamlit run streamlit_deploy.py --server.port 8501 --server.address 0.0.0.0
```

---

## ⚙️ Configuration Options

### Environment Variables
```bash
# Required
GROQ_API_KEY=your_groq_api_key_here

# Optional Performance Tuning
MAX_FILE_SIZE=52428800          # Max upload size (50MB)
PROCESSING_TIMEOUT=300          # Processing timeout (5 minutes)
LOG_LEVEL=INFO                  # Logging level
DEBUG=false                     # Debug mode

# Optional AI Configuration
AI_MODEL=llama-3.1-8b-instant  # AI model selection
AI_TEMPERATURE=0.3              # AI response creativity
AI_MAX_TOKENS=1024              # AI response length

# Optional Database (if using)
DATABASE_URL=sqlite:///./edi_processor.db
REDIS_URL=redis://localhost:6379/0
```

### Streamlit Configuration
Edit `.streamlit/config.toml`:
```toml
[server]
port = 8501
address = "0.0.0.0"
maxUploadSize = 50

[theme]
primaryColor = "#1f77b4"
backgroundColor = "#ffffff"
```

---

## 🔒 Security Configuration

### Production Security Checklist
- [ ] Set strong environment variables
- [ ] Use HTTPS (SSL certificates)
- [ ] Configure firewall rules
- [ ] Set up user authentication if needed
- [ ] Regular security updates
- [ ] Monitor logs for suspicious activity

### SSL/HTTPS Setup
```bash
# Generate SSL certificate (Let's Encrypt)
sudo certbot --nginx -d your-domain.com

# Or use self-signed for testing
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365
```

---

## 📊 Monitoring & Logging

### Application Monitoring
The app includes built-in health checks:
- `/health` endpoint for health monitoring
- Structured logging with timestamps
- Processing metrics and statistics
- Error tracking and reporting

### Log Files
```bash
# Application logs
tail -f logs/edi_processor.log

# System logs (if using systemd)
journalctl -u edi-processor -f

# Docker logs
docker logs -f edi-processor
```

### Performance Monitoring
```bash
# Resource usage
htop
df -h
free -m

# Application metrics
curl http://localhost:8501/health
```

---

## 🚦 Testing Your Deployment

### Quick Health Check
```bash
# Test application health
curl http://localhost:8501/_stcore/health

# Test file upload (using sample)
curl -X POST http://localhost:8501/upload \
  -F "file=@test_278.edi" \
  -F "validate_only=false"
```

### Comprehensive Testing
1. **Upload Test**: Try uploading `test_278.edi`
2. **Processing Test**: Verify full EDI → FHIR conversion
3. **AI Test**: Check AI analysis functionality
4. **Export Test**: Download results in different formats
5. **Performance Test**: Upload multiple files
6. **Error Handling**: Try invalid files

---

## 🔧 Troubleshooting

### Common Issues

#### 1. Import Errors
```bash
# Missing dependencies
pip install -r requirements_deploy.txt

# Python path issues
export PYTHONPATH=/app:$PYTHONPATH
```

#### 2. AI Analysis Not Working
```bash
# Check API key
echo $GROQ_API_KEY

# Test API directly
python -c "from groq import Groq; print(Groq(api_key='your_key').chat.completions.create(model='llama-3.1-8b-instant', messages=[{'role':'user','content':'test'}]))"
```

#### 3. File Upload Issues
```bash
# Check file permissions
chmod 755 uploads/
chmod 755 outputs/

# Check disk space
df -h
```

#### 4. Performance Issues
```bash
# Increase memory limits
export STREAMLIT_SERVER_MAX_UPLOAD_SIZE=100

# Check system resources
top
free -m
```

### Log Analysis
```bash
# Check for errors
grep ERROR logs/edi_processor.log

# Monitor processing
tail -f logs/edi_processor.log | grep "Processing"

# Check AI analysis
tail -f logs/edi_processor.log | grep "AI"
```

---

## 📈 Scaling & Performance

### Horizontal Scaling
```bash
# Run multiple instances with load balancer
docker-compose scale edi-processor=3

# Use nginx for load balancing
upstream edi_backend {
    server localhost:8501;
    server localhost:8502;
    server localhost:8503;
}
```

### Performance Optimization
1. **Caching**: Enable Redis for session caching
2. **CDN**: Use CDN for static assets
3. **Database**: Use PostgreSQL for production
4. **Monitoring**: Set up Prometheus/Grafana
5. **Auto-scaling**: Configure based on CPU/memory usage

---

## 🎯 Production Deployment Checklist

### Pre-Deployment
- [ ] Environment variables configured
- [ ] SSL certificates installed
- [ ] Firewall rules configured
- [ ] Backup strategy in place
- [ ] Monitoring tools setup

### Deployment
- [ ] Build and test Docker image
- [ ] Deploy to staging environment
- [ ] Run full test suite
- [ ] Deploy to production
- [ ] Verify all functionality

### Post-Deployment
- [ ] Monitor application logs
- [ ] Check system resources
- [ ] Verify external integrations
- [ ] Update documentation
- [ ] Train users

---

## 📚 Additional Resources

### Documentation
- [Streamlit Documentation](https://docs.streamlit.io/)
- [Docker Documentation](https://docs.docker.com/)
- [pyx12 Library](https://github.com/azoner/pyx12)
- [FHIR R4 Specification](https://hl7.org/fhir/R4/)

### Support
- **GitHub Issues**: For bug reports and feature requests
- **Documentation**: Check DEPLOYMENT_README.md
- **Logs**: Review application logs for debugging
- **Community**: Streamlit community forums

---

## 🔄 Updates & Maintenance

### Regular Maintenance
```bash
# Update dependencies
pip install --upgrade -r requirements_deploy.txt

# Update Docker images
docker-compose pull
docker-compose up -d

# Backup data
tar -czf backup_$(date +%Y%m%d).tar.gz uploads/ outputs/ logs/
```

### Version Updates
1. Test in staging environment
2. Backup current data
3. Deploy new version
4. Verify functionality
5. Monitor for issues

---

**Your EDI X12 278 Processing Platform is now ready for deployment! 🚀**

For additional support or custom deployment needs, refer to the troubleshooting section or check the application logs. 