import { Canvas } from '@react-three/fiber';
import { OrbitControls, Environment, Grid } from '@react-three/drei';
import { DesignStudio } from './components/DesignStudio';
import { Toolbar } from './components/Toolbar';
import { useState } from 'react';
import { create } from 'zustand';

// Real-time state management
interface DesignState {
  selectedTool: string;
  selectedMaterial: string;
  designElements: any[];
  collaborators: string[];
  setTool: (tool: string) => void;
  addElement: (element: any) => void;
}

export const useDesignStore = create<DesignState>((set) => ({
  selectedTool: 'walls',
  selectedMaterial: 'concrete',
  designElements: [],
  collaborators: [],
  setTool: (tool) => set({ selectedTool: tool }),
  addElement: (element) => set((state) => ({
    designElements: [...state.designElements, element]
  })),
}));

function App() {
  const [viewMode, setViewMode] = useState<'3d' | 'vr' | 'ar' | 'blueprint'>('3d');
  
  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <Header />
      <div className="grid grid-cols-12 gap-4 p-4" style={{ height: 'calc(100vh - 80px)' }}>
        <div className="col-span-3">
          <Toolbar />
        </div>
        <div className="col-span-9 relative">
          <Canvas shadows camera={{ position: [20, 20, 20], fov: 50 }}>
            <ambientLight intensity={0.5} />
            <directionalLight position={[10, 10, 5]} castShadow />
            <DesignStudio viewMode={viewMode} />
            <OrbitControls enablePan enableZoom enableRotate />
            <Environment preset="city" />
            <Grid infiniteGrid />
          </Canvas>
          <ViewControls viewMode={viewMode} onChange={setViewMode} />
        </div>
      </div>
    </div>
  );
}