# 🐳 Design Dock

Design Dock is a full-stack e-commerce platform built with Django that allows users to browse, purchase, and manage premium digital and physical design products. The application provides secure payments, user authentication, admin product management, and a responsive user experience across devices.

- **Live site:** https://design-dock-9a1c5bd13893.herokuapp.com  
- **Repository:** https://github.com/chazeldred55-code/design-dock  

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [User Experience (UX)](#2-user-experience-ux)
3. [Agile Methodology](#3-agile-methodology)
4. [Features](#4-features)
5. [Future Features](#5-future-features)
6. [Database Design](#6-database-design)
7. [Technologies Used](#7-technologies-used)
8. [Testing](#8-testing)
9. [Deployment](#9-deployment)
10. [Credits](#10-credits)

---

## 1. Project Overview

### 🧠 Purpose
Design Dock was created to provide designers and creatives with a curated marketplace for design resources and merchandise.

### 🎯 Site Owner Goals
- Sell design-related products
- Manage inventory and categories
- Process secure payments
- Provide a professional e-commerce experience

### 👤 User Goals
- Browse products
- Filter and search items
- Add products to a shopping bag
- Securely checkout
- Manage account details and view order history

---

## 2. User Experience (UX)

### 🎯 Strategy Plane

#### Target Audience
- Designers
- Students
- Creative professionals
- Small business owners

#### User Stories

**👤 Site User**
- As a user, I want to browse products so I can find something I like.
- As a user, I want to filter products by category.
- As a user, I want to search for products.
- As a user, I want to add items to my bag.
- As a user, I want to securely purchase items.
- As a user, I want to create an account and view order history.

**👑 Site Owner (Admin)**
- As an admin, I want to add products.
- As an admin, I want to edit products.
- As an admin, I want to delete products.
- As an admin, I want to manage product categories.

---

### 🗂 Scope Plane

#### Core Requirements Implemented
- ✅ CRUD functionality
- ✅ Stripe payments
- ✅ User authentication
- ✅ Admin product management
- ✅ Responsive design
- ✅ Deployment to Heroku
- ✅ Testing documented

---

### 🏗 Structure Plane

#### Navigation Structure
- Home
- Products
- Product Detail
- Shopping Bag
- Checkout
- Profile
- Admin Panel

---

### 🖌 Skeleton Plane

Wireframes were created for:
- Home page
- Product listing
- Product detail
- Bag
- Checkout
- Profile

📌 **Wireframes:**  
_Add images to `/documentation/wireframes/` and link them here._

Example:
- Home Wireframe: `![Home Wireframe](documentation/wireframes/home.png)`

---

### 🎨 Surface Plane

Design Dock uses:
- Minimal black/white branding
- Clean layout
- Clear CTA buttons
- Consistent typography
- Responsive Bootstrap grid

---

## 3. Agile Methodology

A GitHub Projects board was used to track:
- User stories
- Development tasks
- Bugs
- Feature implementation

Project development approach:
- Iterative development
- Feature branches where appropriate
- Regular commits
- Clear commit messages

---

## 4. Features

### 🔐 Authentication
- Register
- Login
- Logout
- Profile management

### 🛍 Product Browsing
- Category filtering
- Search functionality
- Product detail view

### 🛒 Shopping Bag
- Add items
- Update quantity
- Remove items
- View totals

### 💳 Secure Checkout
- Stripe payment integration (PaymentIntent)
- Order confirmation
- Webhook handling

### 🛠 Admin Controls
- Add product
- Edit product
- Delete product
- Manage categories

### 📱 Responsive Design
- Mobile-first layout
- Bootstrap grid
- Optimised layouts

---

## 5. Future Features
- Wishlist functionality
- Product reviews
- Discount codes
- Email order confirmation
- Stock tracking dashboard
- Subscription-based design packs

---

## 6. Database Design

### Models Used
- User (Django AllAuth)
- Product
- Category
- Order
- OrderLineItem
- UserProfile

### Relationships
- Product → Category (**ForeignKey**)
- Order → UserProfile (**ForeignKey**)
- OrderLineItem → Product (**ForeignKey**)
- OrderLineItem → Order (**ForeignKey**)

📌 _Optional improvement:_ include an ERD diagram image here.

---

## 7. Technologies Used

### Backend
- Python
- Django

### Database
- SQLite (development)
- PostgreSQL (production)

### Payments
- Stripe API

### Frontend
- HTML5
- CSS3
- Bootstrap
- JavaScript

### Deployment & Storage
- Heroku
- AWS S3 (static/media)
- GitHub

---

## 8. Testing

### Manual Testing

| Feature | Expected Result | Pass |
|--------|------------------|------|
| Add to bag | Item added correctly | ✅ |
| Update quantity | Quantity updates | ✅ |
| Remove item | Item removed | ✅ |
| Stripe payment | Payment succeeds | ✅ |
| Webhook | Order confirmed | ✅ |
| Admin CRUD | Product changes persist | ✅ |

### Validation / Quality
- HTML validated via W3C (no critical issues)
- CSS validated via W3C (no critical issues)
- Python linting via flake8
- Lighthouse testing (no critical errors remain)

📌 _Add screenshots of validation + Lighthouse reports in `/documentation/testing/` and link them here._

---

## 9. Deployment

### Local Development

```bash
git clone https://github.com/chazeldred55-code/design-dock
cd design-dock
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
