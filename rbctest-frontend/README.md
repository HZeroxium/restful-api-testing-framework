# RESTful API Testing Framework - Frontend

A modern, comprehensive React + TypeScript frontend for automated API testing and validation.

## 🚀 Features

### Core Functionality

- **Dataset Management**: Upload and manage OpenAPI specifications
- **Endpoint Discovery**: Automatic extraction of API endpoints from specs
- **Constraint Mining**: AI-powered extraction of API constraints
- **Script Generation**: Automatic creation of Python validation scripts
- **Test Data Generation**: Smart generation of valid and invalid test cases
- **Test Execution**: Execute tests against live APIs with real-time monitoring
- **Verification**: Validate test data and request-response pairs
- **Full Pipeline**: One-click complete testing workflow

### User Experience

- **Modern UI**: Clean, responsive design with Material-UI and Tailwind CSS
- **Real-time Updates**: Polling for live test execution status
- **Advanced Filtering**: Search and filter across all data types
- **Code Viewing**: Syntax-highlighted code display for schemas and scripts
- **Drag & Drop**: Easy file uploads with visual feedback
- **Mobile-Friendly**: Responsive design works on all devices

## 📋 Prerequisites

- Node.js 18+ and npm 9+
- Running instance of the backend API

## 🛠️ Installation

```bash
# Clone the repository
git clone <repository-url>
cd rbctest-frontend

# Install dependencies
npm install

# Configure environment
cp .env.example .env
# Edit .env with your backend API URL

# Start development server
npm run dev
```

The application will be available at http://localhost:5173

## 📁 Project Structure

```
rbctest-frontend/
├── src/
│   ├── app/                    # Redux store configuration
│   ├── types/                  # TypeScript type definitions
│   ├── services/api/          # RTK Query API slices
│   ├── components/
│   │   ├── layout/            # Layout components
│   │   └── common/            # Reusable components
│   ├── features/              # Feature modules
│   │   ├── dashboard/
│   │   ├── datasets/
│   │   ├── endpoints/
│   │   ├── constraints/
│   │   ├── validation-scripts/
│   │   ├── test-data/
│   │   ├── execution/
│   │   └── verification/
│   ├── theme/                 # MUI theme
│   └── main.tsx              # Entry point
├── public/
├── package.json
├── vite.config.ts
├── tailwind.config.js
└── tsconfig.app.json
```

## 🎨 Technology Stack

- **React 19** - UI library
- **TypeScript 5.7** - Type safety
- **Vite 7.1** - Build tool
- **Redux Toolkit** - State management
- **RTK Query** - Data fetching and caching
- **Material-UI (MUI) v7** - Component library
- **Tailwind CSS v4** - Utility-first CSS
- **React Router v7** - Navigation
- **React Hook Form** - Form management
- **Zod** - Schema validation
- **date-fns** - Date formatting
- **React Dropzone** - File uploads
- **React Syntax Highlighter** - Code display

## 🚦 Getting Started

### Quick Start

1. **Upload an OpenAPI Spec**

   - Navigate to Datasets → Upload Spec
   - Drag and drop your OpenAPI JSON/YAML file
   - View extracted endpoints

2. **Run Full Pipeline**
   - Select an endpoint
   - Click "Run Full Pipeline"
   - Enter your API base URL
   - Watch automated testing in action

See [QUICK_START.md](./QUICK_START.md) for detailed usage instructions.

## 🏗️ Architecture

### Component Architecture

#### Layout Components

- `AppLayout`: Main application shell
- `Sidebar`: Collapsible navigation
- `Header`: Page title and breadcrumbs

#### Common Components

- `DataTable`: Generic sortable/filterable table
- `StatusBadge`: Consistent status indicators
- `CodeViewer`: Syntax-highlighted code display
- `FileUploadZone`: Drag-and-drop file uploads
- `ConfirmDialog`: Reusable confirmation dialogs
- `LoadingOverlay`: Loading states
- `ErrorAlert`: Error handling with retry
- `FullPipelineDialog`: Multi-step workflow

### State Management

- **Redux Toolkit** for global state
- **RTK Query** for API calls and caching
- Automatic cache invalidation
- Optimistic updates support

### Routing

- React Router v6 with lazy loading
- Route-based code splitting
- Dynamic breadcrumb generation

## 🎯 Key Features in Detail

### 1. Dataset Management

- Create datasets manually or from OpenAPI specs
- Support for OpenAPI 3.0+ (JSON and YAML)
- Automatic endpoint extraction
- View dataset details and endpoints
- Delete datasets and associated data

### 2. Endpoint Management

- Searchable endpoint list
- Filter by HTTP method, tags, auth requirements
- Detailed endpoint view with tabs:
  - Request/response schemas
  - Mined constraints
  - Generated validation scripts
  - Test data
  - Execution history

### 3. Constraint Mining

- AI-powered constraint extraction
- Supports multiple constraint types:
  - Request parameters
  - Request body
  - Response properties
  - Request-response relationships
- Severity levels (error, warning, info)
- Filter and search capabilities

### 4. Validation Scripts

- Python script generation from constraints
- Syntax-highlighted code view
- Export to .py files
- Accordion view for multiple scripts

### 5. Test Data Generation

- Smart generation based on schemas
- Valid and invalid test case support
- Configurable test count
- Override existing data option
- Detailed test data viewer

### 6. Test Execution

- Execute tests against live APIs
- Real-time status updates with polling
- Auto-refresh for running tests
- Detailed execution results:
  - Individual test case results
  - Request/response data
  - Validation results
  - Timing information
  - Success/failure metrics

### 7. Verification

- Verify test data against validation scripts
- Verify request-response pairs
- Detailed validation feedback
- JSON input support

### 8. Full Pipeline

- End-to-end automated workflow
- Progress tracking with visual stepper
- Step-by-step status updates
- Comprehensive execution summary
- One-click testing solution

## 🎨 Theming & Styling

### MUI Theme

- Custom blue/white color scheme
- Component overrides for consistency
- Responsive breakpoints
- Typography scale

### Tailwind CSS

- Utility classes for rapid development
- Custom configuration matching MUI theme
- Utility components (buttons, cards, inputs)

### Color Palette

- Primary: Blue (#1976d2)
- Secondary: Blue (#42a5f5)
- Success: Green (#4caf50)
- Error: Red (#f44336)
- Warning: Orange (#ff9800)

## 📱 Responsive Design

- Desktop-first with mobile optimizations
- Collapsible sidebar for mobile
- Responsive grid layouts (Grid v2)
- Touch-friendly interactions
- Horizontal scrolling for tables
- Breakpoints: xs, sm, md, lg, xl

## 🔒 Type Safety

- Full TypeScript coverage
- Strict mode enabled
- Path aliases for clean imports
- Complete DTO types matching backend
- Generic utility types
- No any types (except errors)

## 🚀 Performance

- Code splitting with React.lazy
- RTK Query caching
- Memoized components
- Efficient re-renders
- Optimized bundle size

## 🧪 Testing (Recommended)

### Unit Tests

```bash
# Would use Jest + React Testing Library
npm test
```

### Integration Tests

```bash
# Would use MSW for API mocking
npm run test:integration
```

### E2E Tests

```bash
# Would use Playwright or Cypress
npm run test:e2e
```

## 📦 Build & Deploy

### Development

```bash
npm run dev
```

### Production Build

```bash
npm run build
```

### Preview Production Build

```bash
npm run preview
```

### Deploy

The `dist/` directory can be deployed to any static hosting:

- Vercel (recommended)
- Netlify
- AWS S3 + CloudFront
- Azure Static Web Apps
- GitHub Pages

## 🔧 Configuration

### Environment Variables

```ini
VITE_API_BASE_URL=http://localhost:8000
VITE_APP_NAME=RESTful API Testing Framework
VITE_APP_VERSION=0.1.0
VITE_DEBUG=false
```

### Vite Config

- React plugin (SWC for faster builds)
- Development server on port 5173
- Hot module replacement
- Path aliases (@/_ → src/_)

### TypeScript Config

- Strict mode
- Path aliases (@/\*)
- ES2022 target

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📝 Code Style

- ESLint for linting
- Prettier for formatting (recommended)
- TypeScript strict mode
- React hooks conventions
- Component naming: PascalCase
- File naming: PascalCase for components, camelCase for utilities

## 🐛 Troubleshooting

### Cannot connect to backend

- Check `VITE_API_BASE_URL` in `.env`
- Verify backend is running
- Check for CORS issues

### File upload fails

- Verify file is valid OpenAPI spec
- Check file size (< 10MB recommended)
- Review backend logs

### Tests not executing

- Verify base URL is correct
- Check network connectivity
- Review execution error messages

See [QUICK_START.md](./QUICK_START.md) for more troubleshooting tips.

## 📚 Documentation

- [Quick Start Guide](./QUICK_START.md) - Get started quickly
- [Implementation Summary](./IMPLEMENTATION_SUMMARY.md) - Detailed technical documentation
- [Backend Documentation](../README.md) - Backend API documentation

## ✅ Implementation Status

### Completed Features

- [x] Dataset management (CRUD operations)
- [x] OpenAPI spec upload (JSON/YAML)
- [x] Endpoint discovery and listing
- [x] Constraint mining with AI
- [x] Validation script generation
- [x] Test data generation
- [x] Test execution with real-time polling
- [x] Request-response verification
- [x] Full pipeline workflow
- [x] Dashboard with metrics
- [x] Advanced filtering and search
- [x] Code syntax highlighting
- [x] Drag-and-drop file uploads
- [x] Toast notifications (MUI Snackbar)
- [x] Skeleton loaders
- [x] Responsive design (mobile-friendly)
- [x] ARIA labels and accessibility basics
- [x] Error boundaries

## 🗺️ Roadmap

### Planned Features

- [ ] User authentication & JWT
- [ ] Role-based access control
- [ ] Bulk operations (delete, execute)
- [ ] Export capabilities (CSV, JSON)
- [ ] Saved searches/filters
- [ ] Test scheduling/cron jobs
- [ ] Email notifications
- [ ] API documentation viewer
- [ ] Collaborative features (comments, sharing)

### Performance Improvements

- [ ] Virtual scrolling for large tables
- [ ] Code splitting for CodeViewer
- [ ] Service worker for offline support
- [ ] Image optimization

### UX Enhancements

- [ ] Dark mode toggle
- [ ] Customizable theme builder
- [ ] Keyboard shortcuts panel
- [ ] Tour/onboarding flow
- [ ] Undo/redo functionality
- [ ] Custom dashboard layouts

## 📄 License

[License information]

## 👥 Authors

[Author information]

## 🙏 Acknowledgments

- Material-UI team for excellent component library
- Redux Toolkit team for simplifying state management
- Vite team for blazing-fast build tool
- React team for the awesome framework

## 📞 Support

For issues, questions, or contributions:

- Open an issue on GitHub
- Check existing documentation
- Review troubleshooting guide

---

**Built with ❤️ using React + TypeScript**
