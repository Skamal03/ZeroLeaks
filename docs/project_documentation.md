# DLP Solution Documentation

## 1. How It Works
The system acts as a background security guard for your computer. It continuously watches two main "exit points" where data often leaves an organization:
1.  **File System**: It watches a specific folder. If you create or modify a file there, it immediately reads the content.
2.  **Clipboard**: It checks whatever you "Copy" (Ctrl+C).

Once it captures text (from a file or clipboard), it sends it to the **Detector**, which scans it for sensitive information. If sensitive data is found, it logs a warning.

## 2. Features
- **Real-Time Clipboard Monitoring**: Detects sensitive data the moment it enters your clipboard.
- **File System Monitoring**: Watch specific directories for new or modified files containing sensitive data.
- **Hybrid Detection**: Uses both strict rules (Patterns) and smart guessing (AI/NLP).
- **Logging**: Keeps a permanent record of all potential leaks in `dlp_log.log` and displays them in the console.

## 3. What is NLP (Natural Language Processing)?
**NLP** is a field of Artificial Intelligence that helps computers understand human language.
- **Standard Programming (Regex)**: Looks for exact shapes. E.g., "Find a word with an @ symbol". This is rigid.
- **NLP (Spacy)**: Reads the *context*. It knows that "Apple" in "Apple is a fruit" is different from "Apple" in "Apple Inc. stock price".
    - In this project, we use NLP to detect **Named Entities**. These are proper nouns like Names of People, Organizations, Countries, and Monetary values, which are infinite in variety and impossible to list manually.

## 4. Components & Libraries

### Files
| File | Purpose |
| :--- | :--- |
| `main.py` | The **Manager**. It handles arguments (which folder to watch) and starts the two monitors (File & Clipboard) simultaneously. |
| `src/monitor.py` | The **Eyes**. It listens for file changes (using `watchdog`) and clipboard updates (using `pyperclip`). It reads the text and passes it to the detector. |
| `src/detector.py` | The **Brain**. It contains the logic to decide if text is "sensitive". It holds the Regex patterns and loads the NLP model. |
| `src/logger.py` | The **Scribe**. It ensures all detection events are printed to the screen and saved to a file (`dlp_log.log`). |

### Libraries
| Library | Role |
| :--- | :--- |
| **`watchdog`** | Efficiently waits for file system events (Create/Modify) without checking every millisecond. |
| **`pyperclip`** | Allows Python to read/write to the system clipboard. |
| **`spacy`** | The industrial-strength NLP library used for named entity recognition (the AI part). |
| **`re`** | Built-in Python library for Regular Expressions (Pattern matching). |

## 5. Constraints & Rules (Detection Logic)

### File Constraints
- **Monitored Extensions**: The system ONLY checks files ending in:
    - `.txt` (Text files)
    - `.csv` (Spreadsheets/Data)
    - `.log` (Log files)
    - `.md` (Markdown documentation)
    - `.py` (Python source code)
- **Ignored**: Images, PDFs, Word docs (unless raw text readable), or directories are currently ignored to prevent errors.

### Detection Rules (Triggers)
The system flags data as "Sensitive" if it matches:

**A. Strict Patterns (Regex)**
- **Email**: `anything@anything.anything` (e.g., `user@company.com`)
- **SSN**: US Social Security Format `xxx-xx-xxxx`
- **Credit Card**: Sequences of 13-16 digits.
- **Keywords**: "confidential", "private", "secret", "restricted" (Case insensitive).

**B. Smart Context (NLP)**
- **PERSON**: Names of people (e.g., "John Doe", "Alice").
- **ORG**: Companies, Agencies, Institutions (e.g., "Google", "FBI", "United Nations").
- **GPE**: Geopolitical Entities/Countries/Cities (e.g., "New York", "France").
- **MONEY**: Monetary values (e.g., "$500", "1 million dollars").

## 6. How to Test (Verification)

### Testing Email Detection
To manually test if the email detection works:

1.  **Start the Program**:
    Open your terminal and run:
    ```bash
    python main.py --path ./test_monitor
    ```
2.  **Trigger via Clipboard**:
    - Highlight this text: `employee@internal-base.com`
    - Press **Ctrl+C** (Copy).
    - **Check Terminal**: You should see:
      `WARNING - SENSITIVE DATA DETECTED in Clipboard!`
      `WARNING - [EMAIL] employee@internal-base.com (via Regex)`

3.  **Trigger via File**:
    - Keep the program running.
    - Create a new file named `leaked_emails.txt` inside the `test_monitor` folder.
    - Write inside it: `contact: boss@corp.net`.
    - Save the file.
    - **Check Terminal**: You should see:
      `WARNING - SENSITIVE DATA DETECTED in file .../leaked_emails.txt!`
      `WARNING - [EMAIL] boss@corp.net (via Regex)`
