# ConsultEase - Active Context

## Current Focus
The application has undergone significant refactoring to improve stability, maintainability, and adherence to best practices. Core services and controllers have been standardized in terms of configuration, database session management, and logging. The focus remains on preparing for deployment, including hardware integration testing and final documentation updates.

## Recent Changes
- **Centralized Configuration**: `config.py` is now the single source of truth for all configurations. `settings.ini` has been removed. `config.py` now includes all necessary MQTT (including enhanced TLS options like `tls_version` and `tls_cert_reqs`) and RFID (VID/PID now sourced from config) settings.
- **Improved Database Session Management**:
    - Implemented a `@db_operation_with_retry` decorator in `models/base.py` for robust database transactions.
    - Standardized session handling across all controllers (`AdminController`, `FacultyController`, `ConsultationController`, `StudentController`) using the decorator or `try/finally close_db()` blocks.
    - Fixed missing `close_db()` in `RFIDService.refresh_student_data()`.
- **RFID Service (`central_system/services/rfid_service.py`)**:
    - Implemented an in-memory student cache (`self.student_rfid_cache`) populated by `refresh_student_data()`, significantly reducing DB queries per scan.
    - `target_vid` and `target_pid` are now correctly sourced from `config.py`.
    - Improved DB session handling for cache refresh (added `close_db()`).
- **MQTT Service (`central_system/services/mqtt_service.py`)**:
    - Removed direct `settings.ini` access; now uses `get_config()` for all MQTT settings.
    - Client ID is now base_id + random suffix for uniqueness.
    - TLS configuration enhanced: `tls_version` and `tls_cert_reqs` are now configurable via `config.py` and `MQTTService` uses these settings.
- **Controller Refactoring**:
    - `AdminController`, `FacultyController`, `ConsultationController`, `RFIDController`, and the new `StudentController` have been converted to singletons, accessible via `.instance()` methods.
    - Standardized database session management in all controllers.
    - `FacultyController`: Removed subscription to the legacy MQTT topic. Verified `last_seen` attribute usage is correct.
    - `AdminController.authenticate`: Now correctly uses `Admin.is_account_locked` and `Admin.record_login_attempt` from the `Admin` model, fully implementing the DB-backed account lockout logic. Returns more descriptive messages for UI.
    - `ConsultationController`: Replaced `time.sleep()` with a polling loop when checking MQTT connection status before publishing.
    - `RFIDController`:
        - `_notify_callbacks` signature standardized. UI sound playing removed.
        - Added `process_manual_uid()` to handle UIDs entered via UI, streamlining logic from `LoginWindow`.
    - `StudentController`: New controller created to encapsulate student data management.
- **View Layer (`central_system/views/`)**:
    - `LoginWindow`: Simplified keyboard invocation logic.
    - `DashboardWindow`: More efficient `FacultyCard` updates.
    - `AdminDashboardWindow`:
        - Tabs now use singleton controllers.
        - `SystemMaintenanceTab`: Backup/restore methods confirmed to be placeholders showing "Not Implemented".
- **Keyboard Management (`central_system/utils/`)**: Consolidated into `KeyboardManager`.
- **Test/Demo Code**: `_ensure_dr_john_smith_available()` in `main.py` is conditional via config.
- **Model Updates (`central_system/models/`)**:
    - `Admin`: `is_account_locked` and `record_login_attempt` methods confirmed functional for DB-backed lockout.
    - `Faculty`: `last_seen` attribute confirmed present.
- **Logging**: Centralized logging setup. `main.py` now uses `RotatingFileHandler` with `max_size` and `backup_count` from `config.py` for improved log management.

## Recent Changes (Continued from above)
- **Runtime Error Resolution**: Addressed a series of runtime errors including:
    - `AttributeError` and `NameError` issues due to incorrect import paths (e.g., `get_db`, `close_db`, `IconProvider`, `ConsultEaseTheme`, `QSize`) or incorrect attribute/method calls (e.g., `BG_PRIMARY_HOVER`, `Icons.LIST`, `config` object access, `faculty_controller.get_available_faculty`, `consultation.name` in feedback).
    - SQLAlchemy `DetachedInstanceError` in consultation creation and retrieval by implementing eager loading (`joinedload`) in `ConsultationController.get_consultations()` and `get_consultation_by_id()`, and ensuring `create_consultation` returns a fully-loaded object.
    - `RuntimeError: wrapped C/C++ object of type LoadingDialog has been deleted` by adding checks in `NotificationManager.LoadingDialog.run_operation` to ensure the dialog is still visible before attempting to `accept()` or `reject()`.
- **UI Refinements (Consultation History Panel - `central_system/views/consultation_panel.py`)**:
    - Iteratively adjusted `QTableWidget` column widths and resize modes (`setColumnWidth`, `setSectionResizeMode`, `setMinimumSectionSize`) to improve layout and ensure visibility of all data and action buttons.
    - Replaced direct `QTableWidgetItem` for "Status" with a custom-styled `QLabel` set via `setCellWidget` to allow for better visual styling (background color, border, padding) of the status badges.
    - Ensured action buttons ("View", "Cancel") in the history table are clickable and have adequate space.

## Next Steps
- **Hardware Integration Testing**:
    - Thoroughly test with the actual 13.56 MHz RFID reader (verify VID/PID in `config.json`) and various card types.
    - Complete integration testing with ESP32 Faculty Desk Unit, verifying MQTT messages (including TLS if configured), display updates, and BLE presence.
- **MQTT TLS Implementation & Testing**:
    - Generate or obtain necessary TLS certificates/keys.
    - Configure paths and other TLS settings (e.g. `tls_version`, `tls_cert_reqs` if non-default needed) in `config.json`.
    - Test secure MQTT communication between Central System and ESP32.
- **Documentation**:
    - Update user guides (student, faculty, admin) to reflect all UI and functionality changes.
    - Update technical/deployment documentation with details on new configuration options (especially `config.json` for MQTT TLS, RFID VID/PID, logging rotation).
- **Deployment Preparation**:
    - Finalize deployment scripts and procedures for the Raspberry Pi (including ensuring correct file permissions for RFID, log files, and `config.json`).
    - Ensure all dependencies are correctly listed in `requirements.txt`.
- **User Acceptance Testing (UAT)**:
    - Conduct UAT with representative faculty and students to gather feedback.

## Active Decisions and Considerations
- **Configuration Management**: `config.py` (loading `config.json` and environment variables) is the sole source of configuration.
- **Database Session Management**: Primarily through `@db_operation_with_retry` decorator and `try/finally close_db()` for thread-safe, robust operations.
- **Singleton Pattern**: Applied to core controllers and services.
- **MQTT Communication**: Standardized topics. TLS is configurable with fine-grained options. Message persistence in `MQTTService` for QoS > 0 messages.
- **Keyboard Management**: Centralized in `KeyboardManager`.
- **Security**: Bcrypt for admin passwords. DB-backed admin account lockout is implemented.
- **Logging**: Centralized and uses `RotatingFileHandler`.

## Learnings and Project Insights
- **Refactoring Benefits**: Centralizing configuration and standardizing patterns (like DB session management and singletons) significantly improves code clarity, maintainability, and reduces redundancy.
- **Singleton Controllers**: Useful for managing global state and services, simplifying access from different parts of the application (e.g., views).
- **Configuration-driven Behavior**: Using flags in `config.py` (e.g., `ensure_test_faculty_available`, keyboard preferences) makes the application more flexible and easier to manage in different environments.
- **Incremental Refactoring**: Tackling refactoring module by module or feature by feature can make a large task more manageable.
- **Tooling Limitations**: Awareness of tool limitations (e.g., `edit_file` sometimes struggling with complex or repeated edits on the same file) is important; having fallback strategies (like full file replacement or manual review) is key.

## Important Patterns and Preferences

### Code Organization
- Python code follows PEP 8 style guide.
- Modular architecture with clear separation of concerns (models, views, controllers, services, utils).
- **Singleton pattern** for major controllers.
- **Centralized configuration** via `config.py`.
- **Standardized database session management**.
- Proper error handling with informative error messages.
- Resource cleanup with destructors and cleanup methods.

### UI Patterns
- Consistent light theme styling applied via `BaseWindow` and stylesheets.
- Fullscreen toggle via F11 key.
- Manual input fallback provided for hardware-dependent features (RFID scan via UI).
- Status indicators use consistent color coding (green for success, red for error).
- Confirmations required for destructive actions (delete, restore).
- Auto-appearing on-screen keyboard for text input, managed by `KeyboardManager`.
- Informative error messages with suggestions for resolution.
- Views interact with **singleton controller instances**.

### Database Patterns
- SQLAlchemy ORM for database operations.
- Support for both SQLite (development) and PostgreSQL (production).
- `@db_operation_with_retry` decorator for robust transactions.
- Default data creation for easier testing and development (conditionally via config).
- Admin model includes fields for account lockout.

### Security Patterns
- Bcrypt password hashing for admin accounts.
- Plan for DB-backed admin account lockout mechanism.
- Secure credential storage (via `config.py` for service credentials like MQTT).
- MQTT to be secured with TLS.

### Naming Conventions
- CamelCase for class names.
- snake_case for variables and function names.
- UPPERCASE for constants.
- Descriptive names that reflect purpose.
- `instance()` method for accessing singleton objects.

### Testing and Debugging
- Comprehensive error logging (centrally configured).
- Simulation modes for hardware-dependent features (RFID scan).
- Manual input fallbacks for testing.
- Environment variable configuration for different environments, read via `config.py`.
- Conditional enabling of test data/features via `config.py`.