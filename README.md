# AI-Powered Workforce Scheduling and Task Assignment

This repository contains a web-based application developed with **Python** and **Flask** that leverages **Genetic Algorithms**, **Monte Carlo Simulation**, and the **Taguchi Method** to optimize workforce scheduling and task assignment in a project-based production setting. The system is designed for an environment that assumes (theoretically) unlimited capacity but needs intelligent allocation of skilled workers to a variety of production tasks.

## Key Features

### 1. **Genetic Algorithm (GA) for Assignment:**
- Automatically allocates the most suitable employees to each task based on skill levels, experience, and productivity scores.
- Aims to maximize overall "fitness" by matching tasks with the best-fitting workforce.

### 2. **Monte Carlo Simulation:**
- Models various uncertainties like absenteeism (probability of a worker not showing up) and performance fluctuations.
- Runs multiple scenarios to determine average, best, and worst-case outcomes for scheduling efficiency.

### 3. **Taguchi Method for Process Optimization:**
- Analyzes historical data to determine optimal parameter levels (e.g., assembly times) for different product designs.
- Provides insight on how to reduce process variability and overall completion time.

### 4. **Web Application with Flask:**
- Offers a user-friendly interface to manage tasks, employees, and scheduling information in real time.
- Displays optimization results (e.g., assigned workforce, alternative suggestions, improvement ratios) clearly for decision-makers.

### 5. **Unlimited Capacity Assumption:**
- Designed for a project-based production factory where capacity is theoretically unlimited, so the primary goal is to optimize how workforce resources are allocated.

---
## How It Works

### **1. Data Preparation:**
- Project tasks (or "design codes") are stored with information such as estimated assembly times, product details, and required skill levels.
- Employee data includes skill levels, years of experience, and a productivity metric.

### **2. Running the Optimizations:**
- **Genetic Algorithm:** Matches tasks to employees, continuously refining assignments through mutation and crossover until it finds near-optimal or fully optimal solutions.
- **Monte Carlo:** Perturbs the employees' productivity scores and attendance probabilities over multiple simulations, then calculates and saves aggregated results (average fitness, best/worst fitness, etc.).
- **Taguchi:** Uses historical assembly times to compute improved parameter settings, aiming to minimize overall assembly time and variability.

### **3. Interactive Web Interface:**
- Allows adding, deleting, or updating both tasks and employee records.
- Enables viewing the real-time schedule, including who is assigned to which task, as well as seeing any tasks at risk of delay.
- Displays optimization outputs, letting you track workforce utilization and identify areas for improvement.

---
## Installation & Setup

### **1. Clone the Repository:**
```bash
git clone https://github.com/YourUsername/your-repo-name.git
cd your-repo-name
```

### **2. Create and Activate a Virtual Environment (Recommended):**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

### **3. Install Dependencies:**
```bash
pip install -r requirements.txt
```

### **4. Run the Flask App:**
```bash
flask run
```
By default, the application runs on [http://127.0.0.1:5000](http://127.0.0.1:5000).

### **5. Access the Web App:**
- Navigate to `http://127.0.0.1:5000` in your browser.
- Explore the interface to manage tasks, employees, scheduling, and optimizations.

---
## Repository Structure

```
📁 Workforce-Scheduling-AI
├── app.py                  # Main Flask application entry point
├── geneticalgorithm.py      # Genetic Algorithm implementation
├── monte_carlo.py          # Monte Carlo simulation functions
├── taguchi.py              # Taguchi method optimization
├── templates/              # HTML templates for Flask frontend
├── static/                 # CSS, JS, and other static files
├── veri/                   # JSON data files (tasks, employees, results)
├── requirements.txt        # List of dependencies
└── README.md               # This README file
```


