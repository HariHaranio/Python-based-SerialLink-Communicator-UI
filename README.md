# Python-based-SerialLink-Communicator-UI
Python-based GUI for PC-to-microcontroller UART/USART communication, built with Tkinter and PySerial.

# SerialLink Communicator UI

A lightweight Python desktop application for bidirectional UART/USART communication between a PC and a microcontroller. SerialLink provides a graphical interface for sending commands to an embedded system and monitoring the data received from it through a serial COM port.

The application is built with **Python, Tkinter, and PySerial**. It is suitable for testing and debugging microcontroller USART drivers, including bare-metal STM32 projects.

> [!IMPORTANT]
> This serial terminal has been tested with STM32, PIC16F877A, and ESP32-C3 microcontrollers.

## UI Interface
<img width="1026" height="712" alt="image" src="https://github.com/user-attachments/assets/57baef63-586f-464e-96e9-dfe9ec0b6573" />

## Features

- **COM port selection** — detect available serial ports and refresh the list.
- **Configurable baud rate** — choose from `9600`, `19200`, `38400`, `57600`, `115200`, `230400`, `460800`, and `921600` baud.
- **Connect / disconnect status** — connect to a serial device and view the connection status indicator.
- **Transmit data** — send text to the connected device, either with the **Send** button or by pressing **Enter**.
- **Selectable line ending** — append `CRLF` (`\r\n`), `LF` (`\n`), or no line ending.
- **Receive terminal** — display incoming serial text in a terminal-style window.
- **Timestamps** — show or hide timestamps on logged messages.
- **Send history indicator** — display the most recently sent text.
- **Clear terminal** — clear the visible log.
- **Resizable window option** — enable or disable resizing.
- **Responsive receiving** — read serial data in a background thread and process queued messages in batches.
- **Bounded log and queue** — limit retained terminal lines and queued receive messages to help control memory use during high-volume communication.



## Requirements

- Python 3.8 or later (the application uses standard Python libraries plus PySerial).
- Tkinter, which is included with many Python installations. On some Linux distributions, install the system's Tkinter package separately.
- PySerial.

## Installation

1. Clone or download this repository:

   ```bash
   git clone <your-repository-url>
   cd <your-repository-folder>
   ```

2. (Recommended) Create and activate a virtual environment:

   **Windows**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```

   **Linux / macOS**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Install the dependency:

   ```bash
   python -m pip install pyserial
   ```

## Run the application

Run the Python file:

```bash
python serial_terminal.py
```

The application window opens with the available serial ports and a default baud rate of `115200`.

## How to use

1. Connect the microcontroller to the PC through a USB-to-UART adapter or a board's USB virtual COM port.
2. Identify the COM port assigned by the operating system.
3. Open SerialLink and click **Refresh** if the port is not listed.
4. Select the correct port and set the baud rate to match the microcontroller firmware.
5. Click **Connect**. The status indicator turns green when the connection opens successfully.
6. Enter a command in **Send Data** and click **Send**, or press **Enter**. Choose the line ending expected by the firmware.
7. Incoming text appears in the **Serial Terminal**. Use **Hide Timestamps / Show Timestamps** to change timestamp visibility and **Clear Terminal** to clear the log.
8. Click **Disconnect** before changing devices or baud rates.

> [!NOTE]
>  **Important:** A successful connection only means the PC opened the serial port. It does not prove that the MCU's USART configuration, wiring, or firmware is correct.

## How it works

- **Tkinter** builds the graphical interface.
- **PySerial** opens the selected port, transmits UTF-8 encoded text, and reads incoming bytes.
- A **background reader thread** receives serial data so blocking reads do not run in the GUI thread.
- A **thread-safe queue** transfers received messages to the GUI for display.
- The GUI processes queued messages in batches and limits retained terminal lines to reduce UI lag and memory growth.
- Received bytes are decoded as UTF-8; invalid byte sequences are replaced, and null characters are removed. The current implementation uses line-based reading, so incoming data is displayed as text lines rather than as a raw binary/hex stream.

> [!CAUTION]
> Incorrect serial settings may cause communication failures.

## Project structure

```text
.
├── serial_terminal.py
├── README.md
└── docs/
    └── seriallink-ui.png
```

The `docs/seriallink-ui.png` file is an example location for the screenshot. Add the image to that path, or change the Markdown image path to match your repository.

## Limitations and notes

- The current interface is intended for **text-based serial communication**, not binary protocol analysis.
- The reader uses `readline()`, so firmware should send line endings if you want each message to appear promptly as a complete line.
- The application does not currently expose parity, data-bit, stop-bit, or hardware/software flow-control settings in the UI.
- Only one serial connection is managed at a time.
- The receive queue and terminal history have fixed limits; under sustained high-rate input, messages may be dropped or old log lines removed.
- The application does not automatically reset or configure the microcontroller.


> [!TIP]
> ## Troubleshooting

| Problem | Things to check |
|---|---|
| No COM port appears | Reconnect the board, click **Refresh**, check the USB cable and driver, and verify the OS detects a serial device. |
| Connection fails | Ensure another terminal is not using the port and select the correct COM port. |
| No received text | Check MCU TX → PC/adapter RX wiring, common ground, baud rate, firmware transmit logic, and line endings. |
| PC sends but MCU receives nothing | Check PC/adapter TX → MCU RX, GPIO alternate-function setup, USART enable bits, baud-rate calculation, and receive logic. |
| Text is unreadable | Verify baud rate and serial framing on both sides. |
| Messages appear late | The reader uses line-based reads with a serial timeout; ensure the MCU sends a newline/CRLF when appropriate. |
| Port is busy | Close other serial monitor applications before connecting. |

## Technologies

- Python
- Tkinter / ttk
- PySerial
- Threading and queue-based message handling

