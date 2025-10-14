---
config:
  layout: elk
---
flowchart TB
 subgraph subGraph0["User Interface Layer"]
        B["SwotTool"]
        A["User Request"]
  end
 subgraph subGraph1["Core Orchestration Layer"]
        C["SWOTExecutionManager"]
        D["SourceCollectionManager"]
        P1["SwotMemoryService"]
        Q1["Notifier Service"]
  end
 subgraph subGraph12["Generation Request"]
        GEN_REQ["📝 Generation Request"]
        GEN_STEP1["1️⃣ Create Context"]
        GEN_STEP2["2️⃣ Generate Report"]
        GEN_STEP3["3️⃣ Save to Memory"]
        GEN_STEP4["4️⃣ Return Result"]
  end
 subgraph subGraph13["Modification Request"]
        MOD_STEP1["1️⃣ Read Memory"]
        MOD_STEP2["2️⃣ Check Memory Content"]
        MOD_STEP3["3️⃣ Apply Modifications"]
        MOD_STEP4["4️⃣ Save Updated Content"]
        MOD_STEP5["5️⃣ Return Result"]
        MOD_FALLBACK["🔄 Fallback to Generation"]
  end
 subgraph subGraph14["Retrieval Request"]
        RET_STEP1["1️⃣ Read Memory"]
        RET_STEP2["2️⃣ Check Memory Content"]
        RET_STEP3["3️⃣ Return Cached Result"]
        RET_FALLBACK["🔄 Fallback to Generation"]
  end
 subgraph subGraph11["Operation Router"]
        ROUTE["🔀 Operation Router"]
        subGraph12
        subGraph13
        subGraph14
  end
 subgraph subGraph2["Data Processing Layer"]
        Q2["Notifier Service"]
        subGraph11
  end
 subgraph subGraph3["Data Sources Layer"]
        H["Web Search"]
        I["Internal Documents"]
        J["Earnings Calls"]
  end
 subgraph subGraph4["Analysis Components"]
        L["Strengths Analysis"]
        M["Weaknesses Analysis"]
        N["Opportunities Analysis"]
        O["Threats Analysis"]
  end
 subgraph subGraph5["Output Layer"]
        S["ExecutedSWOTPlan"]
        T["Analysis Results"]
  end
 subgraph subGraph7["Strengths"]
        S_GEN["Generate"]
        S_MOD["Modify"]
        S_RET["Retrieve"]
  end
 subgraph subGraph8["Weaknesses"]
        W_GEN["Generate"]
        W_MOD["Modify"]
        W_RET["Retrieve"]
  end
 subgraph subGraph9["Opportunities"]
        O_GEN["Generate"]
        O_MOD["Modify"]
        O_RET["Retrieve"]
  end
 subgraph subGraph10["Threats"]
        T_GEN["Generate"]
        T_MOD["Modify"]
        T_RET["Retrieve"]
  end
 subgraph subGraph6["SWOT Plan Structure"]
        PLAN["📋 SWOT Plan"]
        OBJ@{ label: "🎯 Objective<br>User's analysis goal" }
        STEPS["📝 Steps"]
        subGraph7
        subGraph8
        subGraph9
        subGraph10
  end
    GEN_REQ --> GEN_STEP1
    GEN_STEP1 --> GEN_STEP2
    GEN_STEP2 --> GEN_STEP3
    GEN_STEP3 --> GEN_STEP4
    MOD_STEP1 --> MOD_STEP2
    MOD_STEP2 --> MOD_STEP3 & MOD_FALLBACK
    MOD_STEP3 --> MOD_STEP4
    MOD_STEP4 --> MOD_STEP5
    RET_STEP1 --> RET_STEP2
    RET_STEP2 --> RET_STEP3 & RET_FALLBACK
    ROUTE --> GEN_REQ & MOD_STEP1 & RET_STEP1
    PLAN --> OBJ & STEPS
    STEPS --> subGraph7 & subGraph8 & subGraph9 & subGraph10
    A --> B
    B --> C
    C --> ROUTE
    H --> D
    I --> D
    J --> D
    D --> C
    L --> S
    M --> S
    N --> S
    O --> S
    S --> T
    B -.-> PLAN
    RET_FALLBACK --> subGraph12
    MOD_FALLBACK --> subGraph12
    subGraph12 --> subGraph4
    OBJ@{ shape: rect}
     B:::userInterface
     A:::userInterface
     C:::orchestration
     D:::orchestration
     P1:::memory
     Q1:::notifier
     GEN_REQ:::genRequest
     GEN_STEP1:::genStep
     GEN_STEP2:::genStep
     GEN_STEP3:::genStep
     GEN_STEP4:::genStep
     MOD_STEP1:::modStep
     MOD_STEP2:::modStep
     MOD_STEP3:::modStep
     MOD_STEP4:::modStep
     MOD_STEP5:::modStep
     MOD_FALLBACK:::fallback
     RET_STEP1:::retStep
     RET_STEP2:::retStep
     RET_STEP3:::retStep
     RET_FALLBACK:::fallback
     ROUTE:::router
     Q2:::notifier
     H:::dataSources
     I:::dataSources
     J:::dataSources
     L:::analysis
     M:::analysis
     N:::analysis
     O:::analysis
     S:::output
     T:::output
     S_GEN:::planStep
     S_MOD:::planStep
     S_RET:::planStep
     W_GEN:::planStep
     W_MOD:::planStep
     W_RET:::planStep
     O_GEN:::planStep
     O_MOD:::planStep
     O_RET:::planStep
     T_GEN:::planStep
     T_MOD:::planStep
     T_RET:::planStep
     PLAN:::planStructure
     OBJ:::planElement
     STEPS:::planElement
    classDef userInterface fill:#e3f2fd,stroke:#1976d2,stroke-width:3px
    classDef orchestration fill:#f3e5f5,stroke:#7b1fa2,stroke-width:3px
    classDef processing fill:#fff3e0,stroke:#f57c00,stroke-width:3px
    classDef dataSources fill:#e8f5e8,stroke:#388e3c,stroke-width:3px
    classDef analysis fill:#fce4ec,stroke:#c2185b,stroke-width:3px
    classDef memory fill:#e8f5e8,stroke:#2e7d32,stroke-width:2px
    classDef notifier fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    classDef output fill:#f1f8e9,stroke:#33691e,stroke-width:3px
    classDef planStructure fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    classDef planElement fill:#e1f5fe,stroke:#0277bd,stroke-width:2px
    classDef planStep fill:#fff8e1,stroke:#f57c00,stroke-width:1px
    classDef router fill:#e8eaf6,stroke:#3f51b5,stroke-width:2px
    classDef genRequest fill:#e8f5e8,stroke:#4caf50,stroke-width:2px
    classDef genStep fill:#f1f8e9,stroke:#66bb6a,stroke-width:1px
    classDef modRequest fill:#fff3e0,stroke:#ff9800,stroke-width:2px
    classDef modStep fill:#fff8e1,stroke:#ffb74d,stroke-width:1px
    classDef retRequest fill:#e3f2fd,stroke:#2196f3,stroke-width:2px
    classDef retStep fill:#e1f5fe,stroke:#42a5f5,stroke-width:1px
    classDef fallback fill:#ffebee,stroke:#f44336,stroke-width:2px
