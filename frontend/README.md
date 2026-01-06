# Agent Team Builder - Frontend

## Setup

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build
```

## Project Structure

```
frontend/
├── src/
│   ├── components/     # React components
│   │   ├── AgentBuilder/   # Agent creation/editing
│   │   ├── TeamBuilder/    # Team creation/editing
│   │   ├── Execution/      # Execution UI
│   │   ├── Analytics/      # Analytics dashboard
│   │   └── Common/         # Shared components
│   ├── hooks/          # Custom React hooks
│   ├── services/       # API services
│   ├── stores/         # Zustand stores
│   ├── types/          # TypeScript types
│   ├── utils/          # Utility functions
│   ├── pages/          # Page components
│   ├── App.tsx         # App root
│   └── main.tsx        # Entry point
├── public/             # Static assets
└── index.html          # HTML template
```

## Technologies

- React 18
- TypeScript
- Vite
- TailwindCSS
- React Query
- Zustand
- React Router
