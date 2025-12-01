# TG-Offliner

The TG-Offliner app is designed to download content from Telegram channels and export it as HTML and PDF.

---

## **Quick Start**

### **1. Getting Telegram API Credentials**

1. **Go to https://my.telegram.org**
2. **Sign in** using your phone number
3. **Navigate to "API development tools" https://my.telegram.org/apps** 
4. **Fill out the application creation form:**
   - App title: `TG-Offliner` (or any other name)
   - Short name: `tg-offliner` (or any other)
   - Platform: choose appropriate (e.g., Desktop)
   - Description: optional
5. **Click "Create application"**
6. **Save the obtained credentials:**
   - `api_id` — this is your `API_ID`
   - `api_hash` — this is your `API_HASH`

⚠️ **Important:** Never publish these credentials or add them to git!

### **2. Configuration Setup**
```bash
# Copy the example configuration
cp example.env .env

# Edit the .env file and fill in the obtained credentials:
# API_ID=your_api_id_from_step_1
# API_HASH=your_api_hash_from_step_1
# PHONE=+1XXXXXXXXXX  # Your phone number with country code
```

### **3. Telegram Authorization**
```bash
# Initial authorization (run once)
docker compose run --rm app python authorize_telegram.py

# You will receive a confirmation code via Telegram or SMS
# Enter the received code in the terminal
```

After successful authorization, a `session_name.session` file will be created to store your session.

### **4. Running the Application**

## **Run with Docker**

- **Build and start all services (backend + frontend SSR):**
  ```bash
  docker compose up --build
  ```

- The Flask backend will be available on port **5000**:
  ```
  http://localhost:5000/
  ```

- The Nuxt frontend (SSR) will be available on port **3000**:
  ```
  http://localhost:3000/
  ```

- **Hot-reload:**  
  Any changes in the `tg-offliner-frontend` folder will be reflected immediately in the SSR frontend (no need to rebuild the container).

---

**Note:**  
You no longer need to run the frontend separately with `npm run serve`.  
All services are managed via Docker Compose and work together out of the box.

---

## **Features**

- Export Telegram posts as individual HTML files
- Combine all exported posts into a single PDF file (WIP - work in progress)
- Generate an index file with links to all posts
- Support for grouped messages and media attachments
- Flexible command-line options for controlling the export process

---

## **Security**

⚠️ **Important Security Guidelines:**

- **Never publish the `.env` file** — it contains your personal credentials
- **Never add `*.session*` files to git** — they contain your authorization data
- **The `downloads/` directory** may contain personal data from channels
- Use `.gitignore` to protect sensitive files (already configured in the project)
- After cloning the public repository, create your own `.env` file based on `example.env`

---

## **Testing**

The project has **98 tests** with full coverage of core functionality.

### **Backend Tests (Python)**

- **Run all tests locally:**
  ```bash
  cd tg-offliner
  python -m unittest discover tests/ -v
  ```

- **Run a specific test file:**
  ```bash
  python -m unittest tests.test_api_layouts -v
  ```

- **Basic run in Docker:**
  ```bash
  docker compose run --rm app python tests/run_tests.py
  ```
  Runs all unit tests and outputs a brief summary directly to the console.

- **HTML report:**
  ```bash
  docker compose run --rm app python tests/run_tests.py --html
  ```
  Generates a file in `test_reports/` with a detailed table for each test.

- **Integration tests:**
  ```bash
  docker compose run --rm -e RUN_TELEGRAM_INTEGRATION=1 app python tests/run_tests.py --html
  ```
  Additionally performs import of the test channel `@llamatest`. By default, the test is marked as `skipped` to avoid accessing Telegram unnecessarily.

### **Frontend Tests (JavaScript)**

- **Run all tests locally:**
  ```bash
  cd tg-offliner-frontend
  npm test
  ```

- **Run tests in watch mode:**
  ```bash
  npm test -- --watch
  ```

### **Test Coverage**

- **Backend:** 90 unit tests (unittest)
- **Frontend:** 8 tests (Vitest)
- **New features:** Fully covered tests for layout generation, API endpoints, and frontend service
