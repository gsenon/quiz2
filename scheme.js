/*
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Flask App      │    │   PostgreSQL    │
│                 │    │                  │    │                 │
│ • HTML/CSS/JS   │◄──►│ • Routing        │◄──►│ • Questions     │
│ • Test Interface│    │ • Auth System    │    │ • Test Sessions │
│ • Admin Panel   │    │ • Question Gen   │    │ • Users         │
└─────────────────┘    │ • PDF Generation │    │ • Settings      │
                       └──────────────────┘    └─────────────────┘
                              ▲                         
                              │                         
                       ┌──────────────────┐
                       │   Kubernetes     │
                       │                  │
                       │ • Deployment     │
                       │ • Service        │
                       │ • Ingress        │
                       │ • ConfigMap      │
                       │ • Secrets        │
                       └──────────────────┘
                    
*/