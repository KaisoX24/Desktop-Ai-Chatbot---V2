# Desktop-Ai-Chatbot---V2

graph TD
    %% =========================================
    %% Subgraph: Main UI Thread
    %% =========================================
    subgraph Main_Thread ["Main Thread (UI & Event Loop)"]
        style Main_Thread fill:#2a2a2a,stroke:#555,color:white
        Start([Start main.py]) --> Init[Load Env & Init Client]
        Init --> SetupUI[Setup UI & Start Mainloop]

        %% Sidebar Loading
        SetupUI --> ListSessions["list_sessions() reads index.json"]
        ListSessions --> RenderSidebar[Render Sidebar & Select Last Session]

        %% Main Event Loop
        RenderSidebar --> AwaitInput{Await User Input}

        %% User Send Action Sequence
        AwaitInput -- User clicks Send --> UI_Send["ui.send_message()"]
        UI_Send --> AppendUserUI[Append User Msg to Chatbox]
        AppendUserUI --> UpdateStateUser[Update in-memory STATE obj]
        UpdateStateUser --> SaveSessionUser["session_manager.save_session()"]
        SaveSessionUser --> RefreshSide[Refresh Sidebar Preview]
        RefreshSide --> StartThread[Spawn background worker thread]

        %% UI Queue Processor Loop
        AwaitInput -- "Every 50ms check" --> CheckQueue{"process_ui_queue()"}
        CheckQueue -- Queue Empty --> AwaitInput
        CheckQueue -- Task Found --> RunTask["Execute queued task (do_ui)"]

        %% Handling AI Response on Main Thread
        RunTask --> StreamUI[Stream AI Response to Chatbox]
        StreamUI --> UpdateStateAI["Lazy load STATE & append AI Msg"]
        UpdateStateAI --> SaveSessionAI["session_manager.save_session()"]
        SaveSessionAI --> AwaitInput
    end

    %% =========================================
    %% Subgraph: Background Worker Thread
    %% =========================================
    subgraph Background_Thread ["Background Thread (AI Worker)"]
        style Background_Thread fill:#1a1a1a,stroke:#666,color:white
        StartThread --> WorkerFunc["process_ai_response_worker()"]
        WorkerFunc --> CallAPI["ai_client.get_ai_response_blocking()"]
        CallAPI --> QueueResult["Queue 'do_ui' task into ui_queue"]
    end

    %% =========================================
    %% Subgraph: External & Storage
    %% =========================================
    subgraph Storage_External ["Storage & External API"]
        style Storage_External fill:#333,stroke:#333,color:white
        GroqAPI{{Groq API}}
        FS_Index[(sessions/index.json)]
        FS_Session[("sessions/{sid}.json")]
    end

    %% =========================================
    %% Cross-Subgraph Connections
    %% =========================================
    %% Storage connections
    ListSessions <--> FS_Index
    RenderSidebar <--> FS_Session
    SaveSessionUser --> FS_Session & FS_Index
    SaveSessionAI --> FS_Session & FS_Index

    %% API connections
    CallAPI -- Request --> GroqAPI
    GroqAPI -- Response --> CallAPI

    %% Thread Bridge connections
    QueueResult -.->|"Puts task"| CheckQueue
