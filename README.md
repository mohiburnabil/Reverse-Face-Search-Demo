# 🔍 Reverse Face Search System

A comprehensive multi-service system for reverse face search that combines face detection, face verification, web scraping, and AI-powered summarization to identify and provide detailed information about people from images.

## 🌟 Features

- **Multi-Face Detection**: Automatically detects and extracts multiple faces from images using YOLO
- **Face Verification**: Advanced face matching using ArcFace embeddings and cosine similarity
- **Web Search Integration**: Searches for faces across multiple online platforms
- **LinkedIn Integration**: Specialized LinkedIn profile scraping and verification
- **AI-Powered Summarization**: Generates comprehensive summaries using GPT models
- **Database Integration**: Optional database storage and retrieval for faster searches
- **Telegram Bot Interface**: User-friendly Telegram bot for easy interaction
- **Real-time Processing**: Asynchronous processing for optimal performance

## 🏗️ System Architecture

The system consists of 6 microservices that work together:

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────────┐
│   Telegram Bot  │────│ Face Detection   │────│  Face Verification  │
│   (Port 8080)   │    │   (Port 8080)    │    │    (Port 8111)      │
└─────────────────┘    └──────────────────┘    └─────────────────────┘
         │                       │                        │
         │                       │                        │
         ▼                       ▼                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────────┐
│ FaceCheck API   │    │   Backend API    │    │       Database      |
│  (Port 8888)    │    │   (Port 8000)    │    │                     │
└─────────────────┘    └──────────────────┘    └─────────────────────┘
```

### Service Components

1. **Face Detection Service** (`face_detection_module/`)
   - Uses YOLOv8 for face detection
   - Extracts individual faces from images
   - Returns base64-encoded face images

2. **FaceCheck Service** (`facecheck-service/`)
   - Integrates with external FaceCheck API
   - Manages API key rotation
   - Returns web search results for detected faces

3. **Face Verification Service** (`Face_verification_service/`)
   - Uses ArcFace for face embeddings
   - Performs similarity matching
   - Filters results by confidence thresholds
   - LinkedIn profile verification

4. **Backend API** (`backend/`)
   - Orchestrates the entire pipeline
   - Web scraping and content extraction
   - AI-powered summarization
   - LinkedIn integration

5. **Telegram Bot** (`telegram_bot_v2/` & `telegram_bot_v2_with_DB/`)
   - User interface for the system
   - Handles image uploads and processing
   - Database integration (v2_with_DB version)

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- CUDA-compatible GPU (recommended for face detection and verification)
- Telegram Bot Token
- API Keys (see Environment Variables section)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Reverse-Face-Search
   ```

2. **Create virtual environments for each service**
   ```bash
   # Create conda environments
   conda create -n face-detection python=3.11 -y
   conda create -n face-verification python=3.11 -y
   conda create -n facecheck-service python=3.11 -y
   conda create -n backend python=3.11 -y
   conda create -n telegram-bot python=3.11 -y
   ```

3. **Install dependencies for each service**
   ```bash
   # Face Detection Service
   conda activate face-detection
   cd face_detection_module
   pip install -r requirements.txt

   # Face Verification Service
   conda activate face-verification
   cd Face_verification_service
   pip install -r requirements.txt

   # FaceCheck Service
   conda activate facecheck-service
   cd facecheck-service
   pip install -r requirements.txt

   # Backend Service
   conda activate backend
   cd backend
   pip install -r requirements.txt

   # Telegram Bot
   conda activate telegram-bot
   cd telegram_bot_v2  # or telegram_bot_v2_with_DB
   pip install -r requirements.txt
   ```

### Environment Configuration

Create `.env` files in each service directory:

#### 1. `facecheck-service/.env`
```env
FACECHECK_API_KEY="your-key-1,your-key-2,your-key-3"
```

#### 2. `backend/.env`
```env
OPENAI_API_KEY=your-openai-api-key
GOOGLE_SEARCH_API_KEY=your-google-api-key
x-rapidapi-key=your-rapidapi-key
x-rapidapi-host=linkedin-api8.p.rapidapi.com
```

#### 3. `face_detection_module/.env`
```env
ESRGAN_SCALE=4
```

#### 4. `Face_verification_service/.env`
```env
x-rapidapi-key=your-rapidapi-key
x-rapidapi-host=linkedin-api8.p.rapidapi.com
```

#### 5. `telegram_bot_v2/.env`
```env
TELEGRAM_BOT_V2=your-telegram-bot-token
FACE_DETECTION_API=http://localhost:8080/detect-faces/
FACE_CHECK_API=http://localhost:8888/process-face-check/
SUMMARY_GENERATION_API=http://localhost:8000/process-image-telegram/
```

#### 6. `telegram_bot_v2_with_DB/.env`
```env
TELEGRAM_BOT_V2_2=your-telegram-bot-token
FACE_DETECTION_API=http://localhost:8080/detect-faces/
FACE_CHECK_API=http://localhost:8888/process-face-check/
SUMMARY_GENERATION_API=http://localhost:8000/process-image-telegram/
DB_SEARCH_ENDPOINT=https://your-db-search-endpoint.com/search/
DB_INSERT_ENDPOINT=https://your-db-insert-endpoint.com/insert/
```

### Running the System

Start each service in separate terminal windows:

```bash
# Terminal 1 - Face Detection Service
conda activate face-detection
cd face_detection_module/app
python main.py

# Terminal 2 - FaceCheck Service
conda activate facecheck-service
cd facecheck-service
python main.py

# Terminal 3 - Face Verification Service
conda activate face-verification
cd Face_verification_service/app
python main.py

# Terminal 4 - Backend API
conda activate backend
cd backend
python main.py

# Terminal 5 - Telegram Bot (choose one)
conda activate telegram-bot
cd telegram_bot_v2
python main.py

# OR for database-enabled version
cd telegram_bot_v2_with_DB
python main.py
```

## 📱 Usage

### Telegram Bot Interface

1. **Start the bot**: Send `/start` to your bot
2. **Upload an image**: Send an image as a document (not as a photo)
3. **Wait for processing**: The bot will:
   - Detect faces in the image
   - Search for each face online
   - Verify matches using face similarity
   - Generate a comprehensive summary
   - Return results with confidence scores

### API Endpoints

#### Face Detection Service (Port 8080)
- `POST /detect-faces/` - Detect faces in uploaded image

#### FaceCheck Service (Port 8888)
- `POST /process-face-check/` - Search for faces using FaceCheck API

#### Face Verification Service (Port 8111)
- `POST /face-verification/` - Verify face matches with similarity scoring
- `POST /compare-linkedin` - Compare faces with LinkedIn profile pictures

#### Backend API (Port 8000)
- `GET /process-image-telegram/` - Main processing endpoint for Telegram integration

## 🔧 Configuration

### Face Detection Settings
- **Model**: YOLOv8 Face Detection
- **Confidence Threshold**: Configurable
- **GPU Support**: CUDA-enabled for faster processing

### Face Verification Settings
- **Model**: ArcFace (buffalo_l)
- **Similarity Threshold**: 0.45 (configurable)
- **Score Threshold**: 80 (configurable)

### API Rate Limiting
- **FaceCheck API**: Multiple keys with automatic rotation
- **OpenAI API**: Rate limiting handled automatically
- **LinkedIn API**: Rate limiting via RapidAPI

## 📊 Performance Optimization

- **Asynchronous Processing**: All services use async/await for better performance
- **GPU Acceleration**: CUDA support for face detection and verification
- **Caching**: Face embeddings are cached for faster subsequent searches
- **Database Integration**: Optional database for storing and retrieving results

## 🛠️ Development

### Project Structure
```
Reverse-Face-Search/
├── backend/                    # Main API orchestration
│   ├── main.py                # FastAPI application
│   ├── utils.py               # Core utilities
│   ├── helpers.py             # Helper functions
│   └── page_ranking.py        # Web page ranking
├── face_detection_module/     # Face detection service
│   └── app/
│       ├── main.py           # YOLO face detection
│       └── utils.py          # Detection utilities
├── Face_verification_service/ # Face verification service
│   └── app/
│       ├── main.py           # ArcFace verification
│       └── utils.py          # Verification utilities
├── facecheck-service/         # FaceCheck API integration
│   ├── main.py               # API wrapper
│   └── keyManager.py         # API key management
├── telegram_bot_v2/          # Basic Telegram bot
└── telegram_bot_v2_with_DB/  # Database-enabled bot
```

### Adding New Features

1. **New Face Detection Models**: Modify `face_detection_module/app/helpers.py`
2. **Additional APIs**: Add new services following the microservice pattern
3. **Database Integration**: Extend `telegram_bot_v2_with_DB/` for new storage options
4. **Custom Summarization**: Modify `backend/utils.py` for different AI models

## 🔒 Security Considerations

- **API Key Management**: Use environment variables for all sensitive data
- **Rate Limiting**: Implement proper rate limiting for production use
- **Data Privacy**: Consider data retention policies for uploaded images
- **Input Validation**: Validate all uploaded images and API inputs

## 🐛 Troubleshooting

### Common Issues

1. **CUDA Out of Memory**
   - Reduce batch sizes in face detection
   - Use CPU-only mode for verification

2. **API Key Exhaustion**
   - Check FaceCheck API key rotation
   - Verify API key format in `.env` files

3. **Face Detection Failures**
   - Ensure images are at least 60x60 pixels
   - Check image format compatibility

4. **LinkedIn Integration Issues**
   - Verify RapidAPI credentials
   - Check LinkedIn cookie validity

### Logs

Each service generates detailed logs:
- `face_detection.log` - Face detection service logs
- `face_verification.log` - Face verification logs
- `facecheck.log` - Backend API logs

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📞 Support

For support and questions:
- Create an issue in the repository
- Check the troubleshooting section
- Review the logs for error details

---

**Note**: This system is designed for research and educational purposes. 