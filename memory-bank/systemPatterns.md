# ConsultEase - System Patterns

## System Architecture

### High-Level Architecture
```
┌─────────────────────────┐      MQTT      ┌───────────────────┐
│    Central System       │◄──────────────►│  Faculty Desk Unit │
│    (Raspberry Pi)       │                │     (ESP32)        │
└─────────────┬───────────┘                └───────────────────┘
              │
              │ SQL
              ▼
┌─────────────────────────┐
│      Database           │
│    (PostgreSQL/SQLite)  │
└─────────────────────────┘
```
*(Note: Database can be PostgreSQL or SQLite for dev)*

### Central System Architecture (PyQt)

The Central System follows a layered architecture, broadly aligning with Model-View-Controller (MVC), though with distinct service and utility layers.

```
┌──────────────────────────────────────────────────────────────────┐
│                            UI Layer (Views)                      │
│ (LoginWindow, DashboardWindow, AdminDashboardWindow, Dialogs etc.)│
└───────────────────────────────┬──────────────────────────────────┘
                                │ (Interacts with Controllers)
┌───────────────────────────────▼──────────────────────────────────┐
│                       Controller Layer                           │
│ (RFIDController, FacultyController, ConsultationController,     │
│  AdminController, StudentController - All Singletons)            │
└───────────────────────────────┬──────────────────────────────────┘
                                │ (Utilize Services and Models)
┌───────────────────────────────▼──────────────────────────────────┐
│                         Service Layer                            │
│ (MQTTService, RFIDService, KeyboardManager - Singletons/Managed) │
└───────────────────────────────┬──────────────────────────────────┘
                                │ (Interact with Database / OS)
┌───────────────────────────────▼──────────────────────────────────┐
│                          Data Model Layer (SQLAlchemy)           │
│ (Faculty, Student, Consultation, Admin models)                   │
├──────────────────────────────────────────────────────────────────┤
│                          Utility Layer                           │
│ (config.py, mqtt_topics.py, icons.py, etc.)                      │
└──────────────────────────────────────────────────────────────────┘
```

### Faculty Desk Unit Architecture (ESP32)
*(No significant changes to this high-level view)*
```
┌─────────────────────────┐
│     Display Controller  │
└───────────┬─────────────┘
            │
┌───────────▼─────────────┐
│     Main Controller     │
├─────────────┬───────────┤
│  BLE        │  MQTT     │
│  Scanner    │  Client   │
└─────────────┴───────────┘
```

## Design Patterns

### Central System
1.  **Model-View-Controller (MVC) - Adapted**:
    *   Models: SQLAlchemy models (`Faculty`, `Student`, `Consultation`, `Admin`).
    *   Views: PyQt windows and widgets (`LoginWindow`, `DashboardWindow`, various tabs and dialogs).
    *   Controllers: Dedicated controller classes (`AdminController`, `FacultyController`, `ConsultationController`, `RFIDController`, `StudentController`) manage application logic and mediate between views and models/services.
2.  **Singleton Pattern**:
    *   Applied extensively to core controllers (`AdminController`, `FacultyController`, `ConsultationController`, `RFIDController`, `StudentController`) to ensure a single point of control and state management for their respective domains.
    *   Used for services like `KeyboardManager`, `RFIDService`.
    *   Database engine and session management (`get_db`, `scoped_session`).
3.  **Observer Pattern**:
    *   MQTT service and registered handlers act as observers for topic updates.
    *   PyQt signals/slots mechanism is used extensively for UI updates in response to data changes or events (e.g., RFID scans, faculty status updates).
4.  **Configuration Management Pattern**:
    *   A centralized configuration system (`config.py` loading `config.json`, environment variables, and providing defaults) is used throughout the application. `get_config()` provides access to configuration.
5.  **Database Session Management Pattern**:
    *   Standardized approach using a `@db_operation_with_retry` decorator for write operations and `try/finally close_db()` blocks for read operations to ensure sessions are properly handled and closed.
6.  **Service Layer Pattern**:
    *   Dedicated services (`MQTTService`, `RFIDService`) encapsulate specific functionalities and external interactions.
7.  **Error Handling and Retry Pattern**:
    *   The `@db_operation_with_retry` decorator implements retry logic for database operations.
    *   MQTT service includes reconnection logic.
    *   Consistent logging of errors.

### Faculty Desk Unit
1.  **State Pattern**:
    *   Faculty presence states (Present, Available, Busy, Unavailable - as defined by system).
    *   Connection states for MQTT (Connected, Disconnecting, Reconnecting).
2.  **Command Pattern** (Implicit):
    *   Functions to publish specific MQTT messages or update the display act as commands.

## Data Flow

### Student Consultation Request Flow
*(No major changes, but reflects updated controller involvement)*
1.  Student scans RFID at Central System (`LoginWindow` / `RFIDController` -> `RFIDService`).
2.  `RFIDService` validates student ID against its cache or database.
3.  If valid, `LoginWindow` transitions to `DashboardWindow`.
4.  Student selects faculty and submits consultation request via `DashboardWindow` -> `ConsultationController`.
5.  `ConsultationController` stores request in the database.
6.  `ConsultationController` publishes request via `MQTTService`.
7.  Faculty Desk Unit receives request via MQTT and displays it.
8.  Faculty returns (BLE beacon detected by ESP32).
9.  Faculty Desk Unit updates its status and publishes this via MQTT.
10. `FacultyController` (via `MQTTService`) receives status, updates the database.
11. `DashboardWindow` (observing `FacultyController` or via callbacks) updates faculty status display.

### Faculty Presence Detection Flow
*(No major changes)*
1.  Faculty BLE beacon is detected by ESP32.
2.  Faculty Desk Unit updates local status display.
3.  Status change (e.g., "Available", "Unavailable") is published via MQTT.
4.  Central System (`FacultyController` via `MQTTService`) receives update.
5.  Database is updated with new status by `FacultyController`.
6.  `DashboardWindow` UI refreshes to show current status.

## Critical Implementation Paths

1.  **RFID Authentication & Student Identification**:
    *   `RFIDService` integration, including VID/PID configuration from `config.py`.
    *   Student lookup in `RFIDService` cache and database.
    *   Error handling and clear feedback via `RFIDController` to UI.
2.  **BLE Presence Detection & MQTT Status Updates**:
    *   Reliable beacon scanning and status interpretation on ESP32.
    *   Consistent MQTT message formatting for status updates from ESP32.
    *   `FacultyController` handling these updates and persisting to DB.
3.  **Centralized Configuration Loading & Access**:
    *   `config.py` correctly loading `config.json`, environment variables, and applying defaults.
    *   All modules using `get_config()` for settings.
4.  **Robust Database Operations**:
    *   Consistent use of `@db_operation_with_retry` and session management across all controllers.
    *   Correct handling of SQLAlchemy sessions and engine.
5.  **Singleton Controller Logic & Interaction**:
    *   Ensuring controllers are correctly initialized as singletons.
    *   Views and other components correctly obtaining and using controller instances.
6.  **MQTT Communication (including future TLS)**:
    *   `MQTTService` correctly using settings from `config.py`.
    *   Reliable message passing for all defined topics.
    *   Correct implementation and testing of TLS.
7.  **Real-time UI Updates via Controllers & Services**:
    *   Thread-safe UI updates using signals/slots.
    *   Views correctly registering for and receiving updates from controllers/services.

## Keyboard Integration Pattern

ConsultEase integrates with on-screen keyboards via a centralized `KeyboardManager` class. This manager is configuration-driven through `config.json`.

### Keyboard Integration Architecture

```
┌─────────────────┐      ┌──────────────────┐      ┌───────────────┐
│  Qt Text Input  │──────│  KeyboardManager  │──────│  System       │
│  Widgets        │      │  (Singleton)      │      │  Keyboard     │
└─────────────────┘      └──────────────────┘      └───────────────┘
```

1. Text input widgets (e.g., `QLineEdit`, `QTextEdit`) in the UI layer trigger keyboard visibility requests, typically on focus-in events.
2. The `KeyboardManager` (a singleton service) receives these requests.
3. `KeyboardManager` handles the logic to show or hide the system's on-screen keyboard based on its internal state and the preferences defined in `config.json`.
4. The actual system keyboard is invoked through subprocess calls or DBus interactions, depending on the specific keyboard program being used (e.g., `squeekboard`, `matchbox-keyboard`).

### KeyboardManager Features

The `KeyboardManager` class provides the following key features:

1.  **Configuration-driven**: Keyboard preferences (e.g., `preferred` keyboard, `fallback` keyboard, `show_timeout`, `hide_timeout`) are set in `config.json` and loaded via `get_config()`.
2.  **Priority List**: Attempts to use the `preferred` keyboard first. If unavailable or fails, it tries the `fallback` keyboard.
3.  **Automatic Detection**: Can detect if supported keyboard executables are available on the system.
4.  **State Management**: Tracks the current visibility state of the keyboard.
5.  **Process Management**: Handles the launching and, where necessary, termination of keyboard processes to ensure proper behavior.
6.  **System Integration**: Designed to work with various common Linux on-screen keyboard implementations.
7.  **Show/Hide Triggers**: Automatically shows the keyboard when a registered text input widget gains focus and hides it when focus is lost or shifts to a non-input widget. Explicit show/hide calls are also possible. 