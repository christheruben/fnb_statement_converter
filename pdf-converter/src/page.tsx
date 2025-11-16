import Header from './components/header.tsx'
import { FileUploadDropZone } from './components/file-upload-dropzone.tsx'

export default function Home() {
  return (
    <div className="flex flex-col min-h-screen bg-background">
      <Header />
      <main className="flex-1 flex items-center justify-center px-4 py-12">
        <FileUploadDropZone />
      </main>
    </div>
  )
}
