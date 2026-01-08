# VigilanceHub - Community Safety Platform

![VigilanceHub Logo](https://img.shields.io/badge/VigilanceHub-Safety_Platform-blue)
![Django](https://img.shields.io/badge/Django-4.2-green)
![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3-purple)
![License](https://img.shields.io/badge/License-MIT-yellow)

A modern, community-powered safety platform for reporting incidents, staying informed, and creating safer neighborhoods across Kenya.

## 🚀 Live Demo
[Coming Soon]

## ✨ Features

### 🔒 Core Functionality
- **Incident Reporting**: Users can report crimes, accidents, hazards, or police interactions
- **Safety Map**: Interactive map showing real-time safety heatmaps and incident reports
- **Emergency Services Directory**: Find nearby police stations, hospitals, and fire departments
- **Community Verification**: Community-driven incident verification system
- **Real-time Alerts**: Receive notifications about incidents in your area

### 🎨 Design Features
- **Modern Dark Theme**: Professional dark interface with gradient accents
- **Responsive Design**: Fully responsive across mobile, tablet, and desktop
- **Minimalist UI**: Clean, uncluttered interface focusing on usability
- **Interactive Elements**: Hover effects, smooth transitions, and visual feedback
- **Accessibility**: High contrast ratios and keyboard navigation support

### 👥 User Features
- **Anonymous Reporting**: Option to report incidents without revealing identity
- **User Profiles**: Personal dashboards with activity history
- **Trust Scoring**: Community reputation system for reliable reporters
- **Media Upload**: Support for photo/video evidence with automatic face blurring
- **Location Services**: GPS integration for accurate incident mapping

## 🛠️ Technology Stack

### Backend
- **Framework**: Django 4.2+
- **Database**: PostgreSQL (recommended) / SQLite (development)
- **Authentication**: Django Allauth
- **File Storage**: Django-storages with AWS S3 or local storage
- **API**: Django REST Framework (optional for mobile app)

### Frontend
- **CSS Framework**: Bootstrap 5.3 with custom dark theme
- **Icons**: Bootstrap Icons
- **Maps**: Leaflet.js with OpenStreetMap
- **JavaScript**: Vanilla JS with minimal dependencies
- **Responsive Design**: Mobile-first approach

### Development Tools
- **Version Control**: Git
- **Package Management**: pip
- **Environment Management**: python-dotenv
- **Code Quality**: flake8, black

## 📦 Installation

### Prerequisites
- Python 3.8+
- PostgreSQL (optional for production)
- Git

### Step-by-Step Setup

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/vigilancehub.git
cd vigilancehub
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment variables**
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. **Run migrations**
```bash
python manage.py migrate
```

6. **Create superuser**
```bash
python manage.py createsuperuser
```

7. **Collect static files**
```bash
python manage.py collectstatic
```

8. **Run development server**
```bash
python manage.py runserver
```

Visit `http://localhost:8000` to see the application.

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the root directory:

```env
# Django Settings
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database (PostgreSQL example)
DB_NAME=vigilancehub
DB_USER=postgres
DB_PASSWORD=yourpassword
DB_HOST=localhost
DB_PORT=5432

# Email Configuration (for production)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-password
EMAIL_USE_TLS=True

# Storage (AWS S3 for production)
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
AWS_STORAGE_BUCKET_NAME=your-bucket
```

### Database Setup

**PostgreSQL (Recommended for Production):**
```sql
CREATE DATABASE vigilancehub;
CREATE USER vigilancehub_user WITH PASSWORD 'yourpassword';
GRANT ALL PRIVILEGES ON DATABASE vigilancehub TO vigilancehub_user;
```

**SQLite (Development):**
No additional setup required.

## 📁 Project Structure

```
vigilancehub/
├── core/                    # Django project settings
├── incidents/               # Incident reporting app
│   ├── models.py           # Incident models
│   ├── views.py            # Incident views
│   ├── urls.py             # Incident URLs
│   └── templates/          # Incident templates
├── users/                   # User management app
│   ├── models.py           # User profiles
│   ├── views.py            # User views
│   └── templates/          # User templates
├── emergency/               # Emergency services app
│   ├── models.py           # Service models
│   └── views.py            # Service views
├── static/                  # Static files
│   ├── css/                # Custom CSS
│   ├── js/                 # JavaScript files
│   └── img/                # Images and icons
├── templates/               # Base templates
│   ├── base.html           # Base template
│   ├── includes/           # Template partials
│   └── [page templates]    # All page templates
├── media/                   # User uploaded files
├── requirements.txt         # Python dependencies
├── .env.example            # Environment example
├── manage.py               # Django management
└── README.md               # This file
```

## 🚀 Deployment

### Production Checklist

1. **Set DEBUG=False** in production
2. **Configure ALLOWED_HOSTS** with your domain
3. **Use PostgreSQL** for production database
4. **Set up SSL/TLS** (HTTPS)
5. **Configure static/media file storage**
6. **Set up email backend** for user verification
7. **Configure CORS** if using API
8. **Set up monitoring** and error tracking

### Deployment Options

**Option 1: Docker (Recommended)**
```dockerfile
# Dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["gunicorn", "core.wsgi:application", "--bind", "0.0.0.0:8000"]
```

**Option 2: Heroku**
```bash
heroku create vigilancehub
heroku addons:create heroku-postgresql:hobby-dev
git push heroku main
```

**Option 3: PythonAnywhere**
- Upload project via Git
- Configure virtual environment
- Set up static files
- Configure WSGI file

## 📱 API Endpoints (Optional)

If implementing REST API:

```python
# api/urls.py
urlpatterns = [
    path('api/incidents/', IncidentListAPI.as_view()),
    path('api/incidents/<int:pk>/', IncidentDetailAPI.as_view()),
    path('api/services/', ServiceListAPI.as_view()),
    path('api/reports/', ReportCreateAPI.as_view()),
]
```

## 🔒 Security Features

- **CSRF Protection**: Enabled on all forms
- **XSS Protection**: Django's built-in security
- **SQL Injection Protection**: Django ORM
- **Password Hashing**: PBKDF2 with SHA256
- **File Upload Validation**: Restricted file types and sizes
- **HTTPS Enforcement**: Required in production
- **Rate Limiting**: Optional for API endpoints

## 👥 User Roles

1. **Anonymous Users**
   - View incidents and maps
   - Access emergency services directory
   - Report incidents anonymously

2. **Registered Users**
   - All anonymous features
   - Create user profile
   - Verify/dispute incidents
   - Comment on incidents
   - Receive alerts

3. **Trusted Reporters**
   - All registered user features
   - Higher trust score
   - Priority verification
   - Badge display

4. **Moderators**
   - Manage incident reports
   - Verify/dispute resolution
   - Manage user accounts
   - Content moderation

5. **Administrators**
   - Full system access
   - User management
   - System configuration
   - Data export

## 📊 Data Models

### Incident Model
```python
class Incident(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    incident_type = models.CharField(max_length=50, choices=INCIDENT_TYPES)
    severity = models.CharField(max_length=20, choices=SEVERITY_LEVELS)
    location = models.PointField()
    address = models.CharField(max_length=255)
    county = models.CharField(max_length=100)
    anonymous = models.BooleanField(default=False)
    verified = models.BooleanField(default=False)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

### User Profile Model
```python
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=15, blank=True)
    county = models.CharField(max_length=100)
    trust_score = models.IntegerField(default=0)
    reports_count = models.IntegerField(default=0)
    verified_reports = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
```

## 🎨 Customizing the Theme

### Color Variables
Edit the CSS variables in `base.html`:

```css
:root {
    --primary: #3a86ff;      /* Primary blue */
    --primary-dark: #2667cc; /* Darker blue */
    --secondary: #6c757d;    /* Gray */
    --success: #38b000;      /* Green */
    --danger: #ff006e;       /* Pink/Red */
    --warning: #ffbe0b;      /* Yellow */
    --info: #00bbf9;         /* Cyan */
    --dark-bg: #0a0e17;      /* Dark background */
    --dark-card: #121826;    /* Card background */
    --light-text: #e2e8f0;   /* Light text */
}
```

### Adding Custom CSS
Create a `custom.css` file in `static/css/`:

```css
/* static/css/custom.css */
.custom-feature {
    /* Your custom styles */
}
```

## 🧪 Testing

Run the test suite:

```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test incidents

# Run with coverage
coverage run manage.py test
coverage report
```

## 📈 Performance Optimization

1. **Database Optimization**
   - Add indexes to frequently queried fields
   - Use `select_related` and `prefetch_related`
   - Implement database caching

2. **Frontend Optimization**
   - Minify CSS and JavaScript
   - Optimize images
   - Use CDN for static files

3. **Caching Strategy**
   - Implement Redis for session caching
   - Use template fragment caching
   - Cache API responses

## 🔄 Updates & Maintenance

### Regular Updates
```bash
# Update dependencies
pip install --upgrade -r requirements.txt

# Run migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic

# Restart server
sudo systemctl restart gunicorn
```

### Backup Strategy
```bash
# Database backup
pg_dump -U postgres vigilancehub > backup.sql

# Media files backup
tar -czf media_backup.tar.gz media/
```

## 🤝 Contributing

We welcome contributions! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Development Guidelines
- Follow PEP 8 style guide
- Write docstrings for functions and classes
- Add tests for new features
- Update documentation as needed

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgements

- **Django** - The web framework for perfectionists with deadlines
- **Bootstrap** - The most popular CSS framework
- **Leaflet** - Open-source JavaScript library for interactive maps
- **Bootstrap Icons** - Free, high-quality icons
- **OpenStreetMap** - Free, editable map of the world

## 📞 Support

For support, email: support@vigilancehub.co.ke

## 🚨 Emergency Notice

This platform is for community safety awareness. For actual emergencies:
- **Police**: Call 999 or 112
- **Ambulance/Fire**: Call 911
- **Child Helpline**: Call 116

---

<div align="center">
Made with ❤️ for safer communities in Kenya
</div>
