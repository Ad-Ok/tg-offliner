# TG-Offliner

The TG-Offliner app is designed to download content from Telegram channels and export it as HTML and PDF.

---

## **Usage**

### **Ensure dependencies are installed:**

Install the required dependencies using one of the following commands:

```bash
pip install telethon
```

or

```bash
pip install -r requirements.txt
```

---

### **Run the script:**

Navigate to the folder where the `telegram_export.py` file is located and execute the following command:

```bash
python telegram_export.py --channel <channel_name>
```

Replace `<channel_name>` with the username of the Telegram channel (without `@`).

---

### **Authorization:**

On the first run, the script will ask for an authorization code sent to your Telegram account. Enter the code in the terminal.

---

### **Result:**

After the script finishes:
- The exported HTML files will be saved in the folder specified by the `OUTPUT_DIR` variable (default is `telegram_export`).
- A combined PDF file (`posts_feed.pdf`) will also be generated in the same folder.

If you moved sensitive data to a `.env` file, ensure the `.env` file is in the same directory as the script.

---

## **Command-line Flags**

The script supports the following flags to control its behavior:

1. **`--channel`** (required)  
   Use this flag to specify the Telegram channel to export posts from (without `@`).  
   Example:
   ```bash
   python telegram_export.py --channel example_channel
   ```

2. **`--no-pdf`**  
   Use this flag to download posts as HTML without generating a PDF.  
   Example:
   ```bash
   python telegram_export.py --channel example_channel --no-pdf
   ```

3. **`--only-pdf`**  
   Use this flag to generate a PDF from already downloaded HTML files without downloading new posts.  
   Example:
   ```bash
   python telegram_export.py --channel example_channel --only-pdf
   ```

4. **`--no-index`**  
   Use this flag to skip generating the index file with links to all posts.  
   Example:
   ```bash
   python telegram_export.py --channel example_channel --no-index
   ```

5. **Default behavior (no flags):**  
   If no flags are provided, the script will:
   - Download posts as HTML.
   - Generate a PDF from the downloaded HTML files.
   - Generate an index file with links to all posts.  
   Example:
   ```bash
   python telegram_export.py --channel example_channel
   ```

---

### **Examples**

- **Download only HTML files:**
  ```bash
  python telegram_export.py --channel example_channel --no-pdf
  ```

- **Generate a PDF from existing HTML files:**
  ```bash
  python telegram_export.py --channel example_channel --only-pdf
  ```

- **Download only HTML files without generating an index file:**
  ```bash
  python telegram_export.py --channel example_channel --no-pdf --no-index
  ```

- **Generate a PDF from existing HTML files without generating an index file:**
  ```bash
  python telegram_export.py --channel example_channel --only-pdf --no-index
  ```

- **Perform all actions (default):**
  ```bash
  python telegram_export.py --channel example_channel
  ```

---

## **Features**

- Export Telegram posts as individual HTML files.
- Combine all exported posts into a single PDF file.
- Generate an index file with links to all posts.
- Support for grouped messages and media attachments.
- Flexible command-line options for controlling the export process.

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