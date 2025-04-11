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
python telegram_export.py
```

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

1. **`--no-pdf`**  
   Use this flag to download posts as HTML without generating a PDF.  
   Example:
   ```bash
   python telegram_export.py --no-pdf
   ```

2. **`--only-pdf`**  
   Use this flag to generate a PDF from already downloaded HTML files without downloading new posts.  
   Example:
   ```bash
   python telegram_export.py --only-pdf
   ```

3. **Default behavior (no flags):**  
   If no flags are provided, the script will:
   - Download posts as HTML.
   - Generate a PDF from the downloaded HTML files.  
   Example:
   ```bash
   python telegram_export.py
   ```

---

### **Examples**

- **Download only HTML files:**
  ```bash
  python telegram_export.py --no-pdf
  ```

- **Generate a PDF from existing HTML files:**
  ```bash
  python telegram_export.py --only-pdf
  ```

- **Perform both actions (default):**
  ```bash
  python telegram_export.py
  ```

---

## **Features**

- Export Telegram posts as individual HTML files.
- Combine all exported posts into a single PDF file.
- Support for grouped messages and media attachments.
- Flexible command-line options for controlling the export process.
