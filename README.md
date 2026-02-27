# TG-Offliner

The TG-Offliner app is designed to download content from Telegram channels and export it as HTML and PDF.

## **Features**

### **Channel Management**
- **Download Telegram channels** — Import messages, media, and metadata from any public or private channel you have access to
- **Preview channels** — View channel information before downloading
- **Multiple channel support** — Manage and export multiple channels simultaneously
- **Channel deletion** — Remove downloaded channel data when no longer needed

### **Content Export**
- **HTML export** — Export channel content as clean, standalone HTML files with embedded styles
- **Gallery layout** — Organize media-heavy channels in a visual gallery format
- **Discussion comments** — Include or exclude discussion/reply threads
- **System messages** — Optional inclusion of service messages (user joined, pinned message, etc.)
- **Polls support** — Preserve poll questions and voting options
- **Reposts/forwards** — Control inclusion of forwarded messages

### **Media Handling**
- **Download media** — Automatically download photos, videos, audio, and documents
- **Avatar caching** — Store channel and user avatars locally
- **Thumbnail generation** — Create previews for media files
- **Media organization** — Structured storage in channel-specific directories

### **Post Management**
- **Edit tracking** — Monitor and record changes to posts over time
- **Hide posts** — Mark individual posts as hidden without deleting them
- **Edit history** — View complete edit history with timestamps and changes
- **Persistent edits** — Edit records remain even after channel deletion

### **Customization**
- **Message limits** — Set maximum number of messages to download per channel
- **Selective import** — Choose which message types to include (polls, reposts, system messages, discussions)
- **Layout options** — Different presentation formats for different content types

### **Technical Features**
- **Docker-based deployment** — Easy setup with Docker Compose
- **Persistent storage** — Database and media files preserved across restarts
- **Real-time progress** — Live download status updates
- **Background async import** — Channel imports run in a background thread, returning 202 Accepted immediately
- **Resume downloads** — Resume interrupted imports without re-downloading existing posts and comments
- **Retry with FloodWait handling** — Automatic retries with exponential backoff and Telegram FloodWaitError support
- **Server logs** — View application logs directly from the UI
- **RESTful API** — Backend API for programmatic access
- **Modern frontend** — Nuxt.js-based responsive interface with Tailwind CSS

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

## **Security**

⚠️ **Important Security Guidelines:**

- **Never publish the `.env` file** — it contains your personal credentials
- **Never add `*.session*` files to git** — they contain your authorization data
- **The `downloads/` directory** may contain personal data from channels
- Use `.gitignore` to protect sensitive files (already configured in the project)
- After cloning the public repository, create your own `.env` file based on `example.env`

---

## **Testing**

The project has **121 tests** with full coverage of core functionality.

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

- **Backend:** 113 unit tests (unittest)
- **Frontend:** 8 tests (Vitest)
- **Covers:** API endpoints, layout generation, chunking, backups, async import/resume/retry, FloodWait handling, concurrency
