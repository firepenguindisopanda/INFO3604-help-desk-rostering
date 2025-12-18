graph TB
    subgraph "Client Layer"
        WebBrowser["Web Browser<br/>(HTML/CSS/JS)"]
        NextJSClient["Next.js Frontend<br/>(Vercel)"]
    end

    subgraph "External Services"
        UploadThing["UploadThing<br/>File Storage Service"]
    end

    subgraph "Flask Application (Render)"
        subgraph "MVC Architecture"
            Controllers["Controllers<br/>(Business Logic)"]
            Models["Models<br/>(Data entities)"]
            Views["Views<br/>(Jinja Templates routes)"]
        end
        
        subgraph "API Versions"
            APIV1["Traditional Routes<br/>(HTML Rendering)"]
            APIV2["API v2 Routes<br/>(JSON Responses)"]
        end
    end

    subgraph "Database Layer"
        PostgreSQL["PostgreSQL Database<br/>(Neon)"]
    end

    %% Traditional Web Flow
    WebBrowser -->|HTTP Requests| APIV1
    APIV1 --> Controllers
    Controllers --> Views
    Models --> Controllers
    Views -->|Rendered HTML| WebBrowser

    %% Next.js API Flow
    NextJSClient -->|1. Uploaded Files| UploadThing
    UploadThing -->|2. File URLs| NextJSClient
    NextJSClient -->|3. Registration Data<br/>+ UploadThing URLs| APIV2
    APIV2 --> Controllers

    %% Database Interactions
    PostgreSQL -->|Data| Controllers
    Controllers --> |SQL Queries|PostgreSQL

    %% Styling
    classDef client fill:#e1f5ff,stroke:#01579b,stroke-width:2px
    classDef flask fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef database fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef external fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px

    class WebBrowser,NextJSClient client
    class Controllers,Models,Views,APIV1,APIV2 flask
    class PostgreSQL database
    class UploadThing external