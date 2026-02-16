🐳 Design Dock
Design Dock is a full-stack e-commerce platform built with Django that allows users to browse, purchase, and manage premium digital and physical design products.
The application provides secure payments, user authentication, admin product management, and a responsive user experience across devices.
Live site: https://design-dock-9a1c5bd13893.herokuapp.com�
Repository: https://github.com/chazeldred55-code/design-dock�
Table of Contents
Project Overview
User Experience (UX)
Agile Methodology
Features
Future Features
Database Design
Technologies Used
Testing
Deployment
Credits
1️⃣ Project Overview
🧠 Purpose
Design Dock was created to provide designers and creatives with a curated marketplace for design resources and merchandise.
The site owner’s goal:
Sell design-related products
Manage inventory and categories
Process secure payments
Provide a professional e-commerce experience
User goals:
Browse products
Filter and search items
Add to bag
Securely checkout
Manage account details
2️⃣ User Experience (UX)
🎯 Strategy Plane
Target Audience
Designers
Students
Creative professionals
Small business owners
User Stories
👤 Site User
As a user, I want to browse products so I can find something I like.
As a user, I want to filter products by category.
As a user, I want to search for products.
As a user, I want to add items to my bag.
As a user, I want to securely purchase items.
As a user, I want to create an account and view order history.
👑 Site Owner
As an admin, I want to add products.
As an admin, I want to edit products.
As an admin, I want to delete products.
As an admin, I want to manage product categories.
🗂 Scope Plane
Core Requirements Implemented
✔ CRUD functionality
✔ Stripe payments
✔ User authentication
✔ Admin product management
✔ Responsive design
✔ Deployment to Heroku
✔ Testing documented
🏗 Structure Plane
Navigation structure:
Home
Products
Product Detail
Shopping Bag
Checkout
Profile
Admin Panel
🖌 Skeleton Plane
Wireframes were created for:
Home page
Product listing
Product detail
Bag
Checkout
Profile
(Insert wireframe images here)
🎨 Surface Plane
Design Dock uses:
Minimal black/white branding
Clean layout
Clear CTA buttons
Consistent typography
Responsive Bootstrap grid
3️⃣ Agile Methodology
GitHub Projects board was used to track:
User stories
Development tasks
Bugs
Feature implementation
Project was developed iteratively with:
Feature branches
Regular commits
Clear commit messages
4️⃣ Features
🔐 Authentication
Register
Login
Logout
Profile management
🛍 Product Browsing
Category filtering
Search functionality
Product detail view
🛒 Shopping Bag
Add items
Update quantity
Remove items
View total
💳 Secure Checkout
Stripe payment integration
PaymentIntent
Order confirmation
Webhook handling
🛠 Admin Controls
Add product
Edit product
Delete product
Manage categories
📱 Responsive Design
Mobile-first
Bootstrap grid
Optimised layouts
5️⃣ Future Features
Wishlist functionality
Product reviews
Discount codes
Email order confirmation
Stock tracking dashboard
Subscription-based design packs
6️⃣ Database Design
Models Used:
User (Django AllAuth)
Product
Category
Order
OrderLineItem
UserProfile
Relationships:
Product → Category (ForeignKey)
Order → UserProfile (ForeignKey)
OrderLineItem → Product (ForeignKey)
OrderLineItem → Order (ForeignKey)
7️⃣ Technologies Used
Backend
Python
Django
SQLite (development)
PostgreSQL (production)
Stripe API
Frontend
HTML5
CSS3
Bootstrap
JavaScript
Deployment & Storage
Heroku
AWS S3 (static/media)
GitHub
8️⃣ Testing
Manual Testing
Feature
Expected Result
Pass
Add to bag
Item added correctly
✔
Update quantity
Quantity updates
✔
Remove item
Item removed
✔
Stripe payment
Payment succeeds
✔
Webhook
Order confirmed
✔
Admin CRUD
Product changes persist
✔
Validation
HTML validated via W3C
CSS validated via W3C
Python tested with flake8
Lighthouse performance tested
No critical errors remain.
9️⃣ Deployment
Local Development
Copy code

git clone https://github.com/chazeldred55-code/design-dock
cd design-dock
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
Heroku Deployment
Create Heroku app
Set config vars
Connect GitHub repo
Enable automatic deploys
Add PostgreSQL
Configure Stripe environment variables
🔐 Environment Variables Required
SECRET_KEY
STRIPE_PUBLIC_KEY
STRIPE_SECRET_KEY
STRIPE_WH_SECRET
DATABASE_URL
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY