---
config:
  layout: elk
---
flowchart TB
 subgraph subGraph0["Generator Entry Point"]
        A["Generation Request"]
        B["Component Type"]
        C["Sources"]
  end
 subgraph subGraph8["Request Types"]
        D["Generation"]
        E["Modification"]
  end
 subgraph subGraph1["Prompt Management System"]
        F["Prompt Router"]
        G["Strengths Prompt"]
        H["Weaknesses Prompt"]
        I["Opportunities Prompt"]
        J["Threats Prompt"]
  end
 subgraph subGraph3["Processing Engine"]
        N["Batch Processing"]
        O["LLM Integration"]
        P["Result Assembly"]
  end
 subgraph subGraph7["Prompt Features"]
        CC["Component-Specific Instructions"]
        DD["Output Format Guidelines"]
        EE["Reference Requirements"]
        FF["Analysis Depth Specifications"]
  end
 subgraph subGraph6["Prompt Templates"]
        Y["Strengths Template"]
        Z["Weaknesses Template"]
        AA["Opportunities Template"]
        BB["Threats Template"]
        subGraph7
  end
     F --> G & H & I & J
     Y --> CC
     Z --> CC
     AA --> CC
     BB --> CC
     CC --> DD
     DD --> EE
     EE --> FF
     A --> subGraph8
     B --> subGraph1
     C --> subGraph3
     subGraph8 --> subGraph1
     subGraph1 --> subGraph6
     subGraph3 --> subGraph1
     A:::entry
     B:::entry
     C:::entry
     D:::requestType
     E:::requestType
     F:::promptRouter
     G:::strengthsPrompt
     H:::weaknessesPrompt
     I:::opportunitiesPrompt
     J:::threatsPrompt
     N:::processingEngine
     O:::processingEngine
     P:::processingEngine
     CC:::promptFeature
     DD:::promptFeature
     EE:::promptFeature
     FF:::promptFeature
     Y:::promptTemplate
     Z:::promptTemplate
     AA:::promptTemplate
     BB:::promptTemplate
    classDef entry fill:#e3f2fd,stroke:#1976d2,stroke-width:3px
    classDef requestType fill:#e8f5e8,stroke:#4caf50,stroke-width:2px
    classDef promptRouter fill:#f3e5f5,stroke:#7b1fa2,stroke-width:3px
    classDef strengthsPrompt fill:#e8f5e8,stroke:#4caf50,stroke-width:2px
    classDef weaknessesPrompt fill:#fff3e0,stroke:#ff9800,stroke-width:2px
    classDef opportunitiesPrompt fill:#e1f5fe,stroke:#2196f3,stroke-width:2px
    classDef threatsPrompt fill:#ffebee,stroke:#f44336,stroke-width:2px
    classDef modelRouter fill:#f3e5f5,stroke:#7b1fa2,stroke-width:3px
    classDef strengthsModel fill:#e8f5e8,stroke:#4caf50,stroke-width:2px
    classDef weaknessesModel fill:#fff3e0,stroke:#ff9800,stroke-width:2px
    classDef opportunitiesModel fill:#e1f5fe,stroke:#2196f3,stroke-width:2px
    classDef threatsModel fill:#ffebee,stroke:#f44336,stroke-width:2px
    classDef processingEngine fill:#fff8e1,stroke:#f57c00,stroke-width:2px
    classDef promptTemplate fill:#fce4ec,stroke:#c2185b,stroke-width:2px
    classDef promptFeature fill:#f3e5f5,stroke:#7b1fa2,stroke-width:1px
