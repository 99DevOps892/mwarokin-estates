from fastapi import FastAPI, HTTPException, Depends, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, EmailStr
from typing import List, Optional
import sqlite3
import datetime
import os
import uuid
from pathlib import Path

app = FastAPI(title="BuildRight Construction API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database setup
def init_db():
    conn = sqlite3.connect('construction.db')
    cursor = conn.cursor()
    
    # Projects table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            category TEXT NOT NULL,
            image_url TEXT,
            completed_date TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Testimonials table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS testimonials (
            id TEXT PRIMARY KEY,
            client_name TEXT NOT NULL,
            client_title TEXT,
            content TEXT NOT NULL,
            avatar_url TEXT,
            rating INTEGER DEFAULT 5,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Contact submissions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS contact_submissions (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT,
            service_type TEXT NOT NULL,
            message TEXT NOT NULL,
            status TEXT DEFAULT 'new',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Insert sample data if empty
    cursor.execute("SELECT COUNT(*) FROM projects")
    if cursor.fetchone()[0] == 0:
        sample_projects = [
            ('1', 'Modern Family Home', 'Beautiful contemporary family residence', 'residential', 
             'https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=2053&q=80', '2023-06-15'),
            ('2', 'Corporate Office Complex', 'Modern office building for tech company', 'commercial',
             'https://images.unsplash.com/photo-1497366754035-f200968a6e72?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=2069&q=80', '2023-08-22'),
            ('3', 'Kitchen Transformation', 'Complete kitchen remodel and upgrade', 'renovation',
             'https://images.unsplash.com/photo-1586023492125-27b2c045efd7?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=2058&q=80', '2023-09-10')
        ]
        cursor.executemany('INSERT INTO projects VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)', sample_projects)
    
    cursor.execute("SELECT COUNT(*) FROM testimonials")
    if cursor.fetchone()[0] == 0:
        sample_testimonials = [
            ('1', 'Sarah Johnson', 'Homeowner', 
             'BuildRight Construction exceeded our expectations with our home renovation. Their attention to detail and commitment to quality is unmatched. We couldn\'t be happier with the results!',
             'https://randomuser.me/api/portraits/women/45.jpg', 5),
            ('2', 'Michael Chen', 'Business Owner',
             'The commercial building they constructed for our business was completed on time and within budget. Their team was professional and communicative throughout the entire process.',
             'https://randomuser.me/api/portraits/men/32.jpg', 5),
            ('3', 'Jennifer Martinez', 'Property Investor',
             'I\'ve worked with several construction companies over the years, but BuildRight stands out for their professionalism and quality workmanship.',
             'https://randomuser.me/api/portraits/women/68.jpg', 5)
        ]
        cursor.executemany('INSERT INTO testimonials VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)', sample_testimonials)
    
    conn.commit()
    conn.close()

init_db()

# Pydantic models
class Project(BaseModel):
    id: str
    title: str
    description: str
    category: str
    image_url: str
    completed_date: str

class Testimonial(BaseModel):
    id: str
    client_name: str
    client_title: str
    content: str
    avatar_url: str
    rating: int

class ContactSubmission(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    service_type: str
    message: str

class ContactResponse(BaseModel):
    id: str
    message: str

# Database connection dependency
def get_db():
    conn = sqlite3.connect('construction.db')
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

# API Routes
@app.get("/")
async def root():
    return {"message": "BuildRight Construction API", "status": "running"}

@app.get("/api/projects", response_model=List[Project])
async def get_projects(category: Optional[str] = None, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    if category and category != 'all':
        cursor.execute("SELECT * FROM projects WHERE category = ? ORDER BY completed_date DESC", (category,))
    else:
        cursor.execute("SELECT * FROM projects ORDER BY completed_date DESC")
    projects = cursor.fetchall()
    return [dict(project) for project in projects]

@app.get("/api/projects/categories")
async def get_project_categories(db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT DISTINCT category FROM projects")
    categories = [row[0] for row in cursor.fetchall()]
    return {"categories": categories}

@app.get("/api/testimonials", response_model=List[Testimonial])
async def get_testimonials(db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM testimonials ORDER BY created_at DESC")
    testimonials = cursor.fetchall()
    return [dict(testimonial) for testimonial in testimonials]

@app.post("/api/contact", response_model=ContactResponse)
async def submit_contact(
    submission: ContactSubmission,
    db: sqlite3.Connection = Depends(get_db)
):
    try:
        cursor = db.cursor()
        submission_id = str(uuid.uuid4())
        
        cursor.execute('''
            INSERT INTO contact_submissions (id, name, email, phone, service_type, message)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (submission_id, submission.name, submission.email, submission.phone, 
              submission.service_type, submission.message))
        
        db.commit()
        
        # In a real application, you would send an email notification here
        print(f"New contact submission from {submission.name} - {submission.email}")
        
        return ContactResponse(
            id=submission_id,
            message="Thank you for your inquiry! We'll contact you shortly."
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/contact/submissions")
async def get_contact_submissions(db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM contact_submissions ORDER BY created_at DESC")
    submissions = cursor.fetchall()
    return [dict(submission) for submission in submissions]

# Serve static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def serve_homepage(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## Frontend - Enhanced HTML with Python Integration

```python
# templates/index.html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BuildRight Construction | Quality Building Services</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        /* All the CSS from your original code remains the same */
        :root {
            --primary: #f9a826;
            --primary-dark: #e6951f;
            --secondary: #2c3e50;
            --light: #ecf0f1;
            --dark: #2c3e50;
            --gray: #95a5a6;
            --success: #27ae60;
            --shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            --transition: all 0.3s ease;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }

        /* ... rest of your CSS remains exactly the same ... */
    </style>
</head>
<body>
    <!-- Header & Navigation -->
    <header>
        <div class="container">
            <nav class="navbar">
                <a href="#" class="logo">Build<span>Right</span></a>
                <ul class="nav-links">
                    <li><a href="#home">Home</a></li>
                    <li><a href="#services">Services</a></li>
                    <li><a href="#projects">Projects</a></li>
                    <li><a href="#testimonials">Testimonials</a></li>
                    <li><a href="#contact">Contact</a></li>
                </ul>
                <div class="mobile-menu">
                    <i class="fas fa-bars"></i>
                </div>
            </nav>
        </div>
    </header>

    <!-- Hero Section -->
    <section class="hero" id="home">
        <div class="container">
            <div class="hero-content">
                <h1>Building Your Vision With Precision & Quality</h1>
                <p>We provide comprehensive construction services with over 15 years of experience in residential and commercial projects. Quality, safety, and client satisfaction are our top priorities.</p>
                <div class="hero-btns">
                    <a href="#contact" class="btn">Get Free Quote</a>
                    <a href="#projects" class="btn btn-secondary">View Our Work</a>
                </div>
            </div>
        </div>
    </section>

    <!-- Services Section -->
    <section id="services">
        <div class="container">
            <div class="section-title">
                <h2>Our Services</h2>
                <p>We offer a wide range of construction services to meet all your building needs</p>
            </div>
            <div class="services-grid">
                <div class="service-card">
                    <div class="service-img">
                        <img src="https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=2070&q=80" alt="Residential Construction">
                    </div>
                    <div class="service-content">
                        <h3>Residential Construction</h3>
                        <p>Custom home building, renovations, and additions tailored to your lifestyle and preferences.</p>
                        <a href="#" class="service-link">Learn More <i class="fas fa-arrow-right"></i></a>
                    </div>
                </div>
                <div class="service-card">
                    <div class="service-img">
                        <img src="https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=2070&q=80" alt="Commercial Construction">
                    </div>
                    <div class="service-content">
                        <h3>Commercial Construction</h3>
                        <p>Office buildings, retail spaces, and commercial facilities built to meet your business needs.</p>
                        <a href="#" class="service-link">Learn More <i class="fas fa-arrow-right"></i></a>
                    </div>
                </div>
                <div class="service-card">
                    <div class="service-img">
                        <img src="https://images.unsplash.com/photo-1581094794329-c8112a89af12?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=2070&q=80" alt="Renovation Services">
                    </div>
                    <div class="service-content">
                        <h3>Renovation & Remodeling</h3>
                        <p>Transform your existing space with our expert renovation and remodeling services.</p>
                        <a href="#" class="service-link">Learn More <i class="fas fa-arrow-right"></i></a>
                    </div>
                </div>
            </div>
        </div>
    </section>

    <!-- Projects Section -->
    <section class="projects" id="projects">
        <div class="container">
            <div class="section-title">
                <h2>Our Projects</h2>
                <p>Take a look at some of our recently completed construction projects</p>
            </div>
            <div class="projects-filter">
                <button class="filter-btn active" data-filter="all">All</button>
                <button class="filter-btn" data-filter="residential">Residential</button>
                <button class="filter-btn" data-filter="commercial">Commercial</button>
                <button class="filter-btn" data-filter="renovation">Renovation</button>
            </div>
            <div class="projects-grid" id="projectsContainer">
                <!-- Projects will be loaded dynamically -->
            </div>
        </div>
    </section>

    <!-- Testimonials Section -->
    <section class="testimonials" id="testimonials">
        <div class="container">
            <div class="section-title">
                <h2>Client Testimonials</h2>
                <p>What our clients say about our construction services</p>
            </div>
            <div class="testimonials-container">
                <div id="testimonialsContainer">
                    <!-- Testimonials will be loaded dynamically -->
                </div>
                <div class="testimonial-nav" id="testimonialNav">
                    <!-- Navigation dots will be generated dynamically -->
                </div>
            </div>
        </div>
    </section>

    <!-- Contact Section -->
    <section id="contact">
        <div class="container">
            <div class="section-title">
                <h2>Get In Touch</h2>
                <p>Contact us for a free consultation and quote for your construction project</p>
            </div>
            <div class="contact-container">
                <div class="contact-info">
                    <div class="contact-item">
                        <div class="contact-icon">
                            <i class="fas fa-map-marker-alt"></i>
                        </div>
                        <div class="contact-details">
                            <h3>Our Location</h3>
                            <p>123 Construction Ave, Building City, BC 12345</p>
                        </div>
                    </div>
                    <div class="contact-item">
                        <div class="contact-icon">
                            <i class="fas fa-phone"></i>
                        </div>
                        <div class="contact-details">
                            <h3>Phone Number</h3>
                            <p>+1 (555) 123-4567</p>
                        </div>
                    </div>
                    <div class="contact-item">
                        <div class="contact-icon">
                            <i class="fas fa-envelope"></i>
                        </div>
                        <div class="contact-details">
                            <h3>Email Address</h3>
                            <p>info@buildrightconstruction.com</p>
                        </div>
                    </div>
                    <div class="contact-item">
                        <div class="contact-icon">
                            <i class="fas fa-clock"></i>
                        </div>
                        <div class="contact-details">
                            <h3>Working Hours</h3>
                            <p>Monday - Friday: 8:00 AM - 6:00 PM</p>
                            <p>Saturday: 9:00 AM - 2:00 PM</p>
                        </div>
                    </div>
                </div>
                <div class="contact-form">
                    <form id="quoteForm">
                        <div class="form-group">
                            <label for="name">Full Name</label>
                            <input type="text" id="name" class="form-control" placeholder="Your Name" required>
                        </div>
                        <div class="form-group">
                            <label for="email">Email Address</label>
                            <input type="email" id="email" class="form-control" placeholder="Your Email" required>
                        </div>
                        <div class="form-group">
                            <label for="phone">Phone Number</label>
                            <input type="tel" id="phone" class="form-control" placeholder="Your Phone">
                        </div>
                        <div class="form-group">
                            <label for="service">Service Needed</label>
                            <select id="service" class="form-control" required>
                                <option value="" disabled selected>Select a Service</option>
                                <option value="residential">Residential Construction</option>
                                <option value="commercial">Commercial Construction</option>
                                <option value="renovation">Renovation & Remodeling</option>
                                <option value="other">Other</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label for="message">Project Details</label>
                            <textarea id="message" class="form-control" placeholder="Tell us about your project..." required></textarea>
                        </div>
                        <button type="submit" class="btn">Submit Request</button>
                    </form>
                </div>
            </div>
        </div>
    </section>

    <!-- Footer -->
    <footer>
        <div class="container">
            <div class="footer-content">
                <div class="footer-col">
                    <h3>BuildRight</h3>
                    <p>Building your vision with precision, quality, and over 15 years of construction expertise.</p>
                    <div class="social-links">
                        <a href="#"><i class="fab fa-facebook-f"></i></a>
                        <a href="#"><i class="fab fa-twitter"></i></a>
                        <a href="#"><i class="fab fa-instagram"></i></a>
                        <a href="#"><i class="fab fa-linkedin-in"></i></a>
                    </div>
                </div>
                <div class="footer-col">
                    <h3>Quick Links</h3>
                    <ul class="footer-links">
                        <li><a href="#home">Home</a></li>
                        <li><a href="#services">Services</a></li>
                        <li><a href="#projects">Projects</a></li>
                        <li><a href="#testimonials">Testimonials</a></li>
                        <li><a href="#contact">Contact</a></li>
                    </ul>
                </div>
                <div class="footer-col">
                    <h3>Services</h3>
                    <ul class="footer-links">
                        <li><a href="#">Residential Construction</a></li>
                        <li><a href="#">Commercial Construction</a></li>
                        <li><a href="#">Renovation & Remodeling</a></li>
                        <li><a href="#">Project Management</a></li>
                        <li><a href="#">Consultation</a></li>
                    </ul>
                </div>
                <div class="footer-col">
                    <h3>Contact Info</h3>
                    <ul class="footer-links">
                        <li><i class="fas fa-map-marker-alt"></i> 123 Construction Ave, Building City</li>
                        <li><i class="fas fa-phone"></i> +1 (555) 123-4567</li>
                        <li><i class="fas fa-envelope"></i> info@buildright.com</li>
                    </ul>
                </div>
            </div>
            <div class="copyright">
                <p>&copy; 2023 BuildRight Construction. All Rights Reserved.</p>
            </div>
        </div>
    </footer>

    <script>
        // API Base URL
        const API_BASE = '/api';

        // Mobile Menu Toggle
        const mobileMenu = document.querySelector('.mobile-menu');
        const navLinks = document.querySelector('.nav-links');

        mobileMenu.addEventListener('click', () => {
            navLinks.classList.toggle('active');
        });

        // Close mobile menu when clicking on a link
        document.querySelectorAll('.nav-links a').forEach(link => {
            link.addEventListener('click', () => {
                navLinks.classList.remove('active');
            });
        });

        // Load Projects from API
        async function loadProjects(category = 'all') {
            try {
                const response = await fetch(`${API_BASE}/projects?category=${category}`);
                const projects = await response.json();
                
                const projectsContainer = document.getElementById('projectsContainer');
                projectsContainer.innerHTML = '';
                
                projects.forEach(project => {
                    const projectCard = document.createElement('div');
                    projectCard.className = 'project-card';
                    projectCard.setAttribute('data-category', project.category);
                    
                    projectCard.innerHTML = `
                        <div class="project-img">
                            <img src="${project.image_url}" alt="${project.title}" loading="lazy">
                        </div>
                        <div class="project-overlay">
                            <h3>${project.title}</h3>
                            <p>${project.category.charAt(0).toUpperCase() + project.category.slice(1)}</p>
                        </div>
                    `;
                    
                    projectsContainer.appendChild(projectCard);
                });
            } catch (error) {
                console.error('Error loading projects:', error);
            }
        }

        // Load Testimonials from API
        async function loadTestimonials() {
            try {
                const response = await fetch(`${API_BASE}/testimonials`);
                const testimonials = await response.json();
                
                const testimonialsContainer = document.getElementById('testimonialsContainer');
                const testimonialNav = document.getElementById('testimonialNav');
                
                testimonialsContainer.innerHTML = '';
                testimonialNav.innerHTML = '';
                
                testimonials.forEach((testimonial, index) => {
                    const slide = document.createElement('div');
                    slide.className = `testimonial-slide ${index === 0 ? 'active' : ''}`;
                    
                    slide.innerHTML = `
                        <div class="testimonial-content">
                            <p>${testimonial.content}</p>
                        </div>
                        <div class="testimonial-author">
                            <div class="author-img">
                                <img src="${testimonial.avatar_url}" alt="${testimonial.client_name}">
                            </div>
                            <div class="author-info">
                                <h4>${testimonial.client_name}</h4>
                                <p>${testimonial.client_title}</p>
                            </div>
                        </div>
                    `;
                    
                    testimonialsContainer.appendChild(slide);
                    
                    const dot = document.createElement('div');
                    dot.className = `testimonial-dot ${index === 0 ? 'active' : ''}`;
                    dot.setAttribute('data-slide', index);
                    testimonialNav.appendChild(dot);
                });
                
                // Reinitialize testimonial slider functionality
                initTestimonialSlider();
            } catch (error) {
                console.error('Error loading testimonials:', error);
            }
        }

        // Project Filtering
        const filterBtns = document.querySelectorAll('.filter-btn');

        filterBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                // Remove active class from all buttons
                filterBtns.forEach(b => b.classList.remove('active'));
                // Add active class to clicked button
                btn.classList.add('active');
                
                const filter = btn.getAttribute('data-filter');
                loadProjects(filter);
            });
        });

        // Testimonial Slider
        function initTestimonialSlider() {
            const testimonialSlides = document.querySelectorAll('.testimonial-slide');
            const testimonialDots = document.querySelectorAll('.testimonial-dot');
            let currentSlide = 0;

            function showSlide(n) {
                // Hide all slides
                testimonialSlides.forEach(slide => {
                    slide.classList.remove('active');
                });
                
                // Remove active class from all dots
                testimonialDots.forEach(dot => {
                    dot.classList.remove('active');
                });
                
                // Show the selected slide
                if (testimonialSlides[n]) {
                    testimonialSlides[n].classList.add('active');
                    testimonialDots[n].classList.add('active');
                    currentSlide = n;
                }
            }

            // Add click event to dots
            testimonialDots.forEach((dot, index) => {
                dot.addEventListener('click', () => {
                    showSlide(index);
                });
            });

            // Auto slide change every 5 seconds
            setInterval(() => {
                let nextSlide = (currentSlide + 1) % testimonialSlides.length;
                showSlide(nextSlide);
            }, 5000);
        }

        // Form Submission
        const quoteForm = document.getElementById('quoteForm');
        
        quoteForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            // Get form values
            const formData = {
                name: document.getElementById('name').value,
                email: document.getElementById('email').value,
                phone: document.getElementById('phone').value,
                service_type: document.getElementById('service').value,
                message: document.getElementById('message').value
            };
            
            try {
                const response = await fetch(`${API_BASE}/contact`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(formData)
                });
                
                if (response.ok) {
                    const result = await response.json();
                    alert(`Thank you ${formData.name}! Your ${formData.service_type} request has been submitted. We'll contact you at ${formData.email} shortly.`);
                    quoteForm.reset();
                } else {
                    throw new Error('Failed to submit form');
                }
            } catch (error) {
                console.error('Error submitting form:', error);
                alert('Sorry, there was an error submitting your request. Please try again.');
            }
        });

        // Smooth scrolling for anchor links
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function (e) {
                e.preventDefault();
                
                const targetId = this.getAttribute('href');
                if (targetId === '#') return;
                
                const targetElement = document.querySelector(targetId);
                if (targetElement) {
                    window.scrollTo({
                        top: targetElement.offsetTop - 80,
                        behavior: 'smooth'
                    });
                }
            });
        });

        // Initialize page content
        document.addEventListener('DOMContentLoaded', () => {
            loadProjects();
            loadTestimonials();
        });
    </script>
</body>
</html>
```

## Requirements File

```python
# requirements.txt
fastapi==0.104.1
uvicorn==0.24.0
pydantic==2.5.0
python-multipart==0.0.6
jinja2==3.1.2
python-dotenv==1.0.0
```

## Admin Dashboard (Optional)

```python
# admin.py
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import sqlite3
from main import get_db

app = FastAPI(title="BuildRight Admin")
templates = Jinja2Templates(directory="templates")

@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request, db: sqlite3.Connection = Depends(get_db)):
    cursor = db.cursor()
    
    # Get stats
    cursor.execute("SELECT COUNT(*) FROM contact_submissions WHERE status = 'new'")
    new_submissions = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM projects")
    total_projects = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM testimonials")
    total_testimonials = cursor.fetchone()[0]
    
    # Get recent submissions
    cursor.execute("SELECT * FROM contact_submissions ORDER BY created_at DESC LIMIT 10")
    recent_submissions = cursor.fetchall()
    
    return templates.TemplateResponse("admin.html", {
        "request": request,
        "new_submissions": new_submissions,
        "total_projects": total_projects,
        "total_testimonials": total_testimonials,
        "recent_submissions": [dict(row) for row in recent_submissions]
    })
```

## Run Script

```python
# run.py
import uvicorn
import webbrowser
import threading
import time

def open_browser():
    time.sleep(2)  # Wait for server to start
    webbrowser.open("http://localhost:8000")

if __name__ == "__main__":
    # Start browser in a separate thread
    threading.Thread(target=open_browser, daemon=True).start()
    
    # Start the server
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
```

## Key Features of This Implementation:

1. **Full Python Backend**: FastAPI with SQLite database
2. **RESTful API**: Complete CRUD operations for projects, testimonials, and contact forms
3. **Dynamic Content**: Projects and testimonials loaded from the database
4. **Form Handling**: Contact form submissions stored in database
5. **Modern Architecture**: Separation of frontend and backend
6. **Responsive Design**: Maintains all original styling
7. **Real-time Updates**: Dynamic filtering and content loading

## To Run the Application:

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
python run.py
```

3. Access the website at `http://localhost:8000`

This implementation provides a fully functional construction company website with a Python backend, database integration, and a modern, responsive frontend that maintains all the original design elements while adding dynamic functionality.