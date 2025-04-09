the tg-offliner app made for download content from telegram channels.

usage:

To run this script, follow these steps:

Ensure dependencies are installed:

```
pip install telethon
```

Make sure the telethon library is installed. If not, install it using:
Run the script:
```
python telegram_export.py
```

Navigate to the folder where the telegram_export.py file is located and execute the following command:
Enter the authorization code:

On the first run, the script will ask for an authorization code sent to your Telegram account. Enter the code in the terminal.
Result:

After the script finishes, the exported HTML files will be saved in the folder specified by the output_dir variable (default is telegram_export).
If you moved sensitive data to a .env file, ensure the .env file is in the same directory as the script.
