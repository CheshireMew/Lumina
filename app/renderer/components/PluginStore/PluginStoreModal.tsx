import React, { useState, useEffect } from 'react';
import './PluginStoreModal.css';
import GalgameSelect from './GalgameSelect';
import GalgameToggle from './GalgameToggle';
import PluginConfigModal from './PluginConfigModal';
import { usePluginManager, PluginStatus } from '../../hooks/usePluginManager'; // [Refactor] Import Hook
import { API_CONFIG } from '../../config';

interface PluginStoreModalProps {
  isOpen: boolean;
  onClose: () => void;
  onOpenLLMSettings?: () => void;
}

const PluginCardSkeleton = () => (
    <div className="plugin-card skeleton-card">
        <div className="card-header">
            <div className="skeleton skeleton-icon"></div>
            <div className="header-text">
                <div className="skeleton skeleton-title"></div>
                <div className="skeleton skeleton-desc"></div>
                <div className="skeleton skeleton-desc-short"></div>
            </div>
            <div className="skeleton skeleton-toggle"></div>
        </div>
    </div>
);

const PluginStoreModal: React.FC<PluginStoreModalProps> = ({ isOpen, onClose, onOpenLLMSettings }) => {
  const [activeTab, setActiveTab] = useState<'skill' | 'tts' | 'stt' | 'system' | 'other'>('skill');
  
  // [Refactor] Use Hook
  const { plugins, isLoading, refreshPlugins, togglePlugin, updateConfig } = usePluginManager();
  
  const [configPlugin, setConfigPlugin] = useState<PluginStatus | null>(null); // Plugin being configured
  
  // [NEW] Permission Modal State
  const [pendingPlugin, setPendingPlugin] = useState<PluginStatus | null>(null);
  
  // [NEW] Drag & Drop State
  const [dragActive, setDragActive] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<string | null>(null); // "uploading", "success", "error"
  
  // [Architecture 4.2] Tier C: Real-time Transit States
  const [transitStates, setTransitStates] = useState<{[id: string]: string}>({});

  // Initial Fetch Only
  useEffect(() => {
    if (isOpen) {
        refreshPlugins();
    }
  }, [isOpen, refreshPlugins]);

  // Drag Handlers
  const handleDrag = function(e: React.DragEvent) {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = function(e: React.DragEvent) {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleUpload(e.dataTransfer.files[0]);
    }
  };

  const handleUpload = async (file: File) => {
      console.log("Uploading plugin:", file.name);
      if (!file.name.endsWith('.zip')) {
          alert("Only .zip files are supported!");
          return;
      }
      
      setUploadStatus("uploading");
      const formData = new FormData();
      formData.append('file', file);

      try {
            const res = await fetch(`${API_CONFIG.BASE_URL}/plugins/upload`, {
              method: 'POST',
              body: formData
          });

          // [Robustness] Handle non-JSON errors (e.g. Nginx 502, Proxy errors)
          const text = await res.text();
          let data;
          try {
              data = JSON.parse(text);
          } catch (e) {
              data = { detail: text || res.statusText };
          }

          if (res.ok) {
              setUploadStatus("success");
              alert(`Plugin installed: ${data.id || 'Unknown'}\nPlease restart backend to load.`);
          } else {
              setUploadStatus("error");
              alert(`Upload failed: ${data.detail || text.slice(0, 100)}`);
          }
      } catch (e: any) {
          console.error(e);
          setUploadStatus("error");
          alert("Upload error: " + e.message);
      } finally {
          setUploadStatus(null);
          await refreshPlugins();
      }
  };

  // [Architecture 4.2] Tier C: WebSocket Response Handler
  useEffect(() => {
    const handleStatusUpdate = (e: any) => {
        const { plugin_id, status } = e.detail;
        console.log(`[PluginStore] Real-time Status: ${plugin_id} -> ${status}`);

        setTransitStates(prev => ({ ...prev, [plugin_id]: status }));

        // Final States: Sync back via refresh
        if (status === 'enabled' || status === 'disabled') {
            refreshPlugins();
            
            // Clear transit state after short delay
            setTimeout(() => {
                setTransitStates(prev => {
                    const next = {...prev};
                    delete next[plugin_id];
                    return next;
                });
            }, 500);
        }
    };

    window.addEventListener('lumina:plugin_status', handleStatusUpdate);
    return () => window.removeEventListener('lumina:plugin_status', handleStatusUpdate);
  }, [refreshPlugins]);

  // [Refactor] Use Hook for Toggle
  const executeToggle = async (plugin: PluginStatus, newState: boolean) => {
    console.log(`[PluginStore] Executing Toggle ${plugin.id} to ${newState}`);
    
    // [OPTIMISTIC UPDATE] - handled by hook logic mostly, but we can rely on refresh
    setTransitStates(prev => ({ ...prev, [plugin.id]: newState ? 'enabling' : 'disabling' }));
    
    await togglePlugin(plugin, newState);
    
    // Clear transit state (if WebSocket didn't already)
    // Actually wait a bit? Hook handles refresh.
    // [FIX] Do NOT clear specific transit state optimistically. 
    // Wait for WebSocket 'lumina:plugin_status' event to confirm real state.
    // Add a safety release only (in case WS fails)
    setTimeout(() => {
         setTransitStates(prev => {
             const next = {...prev};
             // Only clear if still in transitional state (hasn't been handled by WS)
             if (next[plugin.id] === (newState ? 'enabling' : 'disabling')) {
                 delete next[plugin.id];
             }
             return next;
         });
    }, 15000); // 15s Safety Timeout for heavy models
  };

  const handleToggle = (plugin: PluginStatus, newState: boolean) => {
      // If turning ON and has permissions, show confirmation
      if (newState && plugin.permissions && plugin.permissions.length > 0) {
          setPendingPlugin(plugin);
          return;
      }
      executeToggle(plugin, newState);
  };

  const handleConfirmPermission = () => {
      if (pendingPlugin) {
          executeToggle(pendingPlugin, true);
          setPendingPlugin(null);
      }
  };

  // [Refactor] Use Hook for Config
  const handleSaveConfig = async (key: string, value: string) => {
    if (!configPlugin) return;
    await updateConfig(configPlugin, key, value);
  };

  if (!isOpen) return null;

  const filteredPlugins = plugins.filter(p => {
      // 1. Direct Category Match
      if (p.category === activeTab) return true;
      

      
      return false;
  });
  
  // Group by Function Tag
  const groupedPlugins: {[tag: string]: PluginStatus[]} = {};
  filteredPlugins.forEach(p => {
    const tag = p.func_tag || "General";
    if (!groupedPlugins[tag]) groupedPlugins[tag] = [];
    groupedPlugins[tag].push(p);
  });

  return (
    <div className="plugin-modal-overlay">
      <div className="plugin-modal-container glass-panel">
        <div className="plugin-header">
          <h2>🧩 Plugin Store</h2>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>

        <div className="plugin-tabs">
          <button className={activeTab === 'skill' ? 'active' : ''} onClick={() => setActiveTab('skill')}>Skills</button>
          <button className={activeTab === 'tts' ? 'active' : ''} onClick={() => setActiveTab('tts')}>Voice Output</button>
          <button className={activeTab === 'stt' ? 'active' : ''} onClick={() => setActiveTab('stt')}>Voice Input</button>
          <button className={activeTab === 'system' ? 'active' : ''} onClick={() => setActiveTab('system')}>System</button>
          <button className={activeTab === 'other' ? 'active' : ''} onClick={() => setActiveTab('other')}>Other</button>
          <div style={{marginLeft: 'auto', display: 'flex', alignItems: 'center'}}>
            <label className="import-btn" style={{cursor:'pointer', fontSize: '0.9em', opacity: 0.8}}>
                📥 Install .zip
                <input 
                    type="file" 
                    accept=".zip" 
                    style={{display: 'none'}} 
                    onChange={(e) => {
                        if (e.target.files && e.target.files[0]) handleUpload(e.target.files[0]);
                    }}
                />
            </label>
          </div>
        </div>

        <div 
            className={`plugin-content ${dragActive ? 'drag-active' : ''}`}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            style={{position: 'relative'}}
        >
          {dragActive && (
              <div className="drag-overlay" style={{
                  position: 'absolute', top: 0, left: 0, right: 0, bottom: 0,
                  background: 'rgba(0,0,0,0.7)', zIndex: 100,
                  display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
                  backdropFilter: 'blur(4px)', borderRadius: '12px', border: '2px dashed #a29bfe'
              }}>
                  <div style={{fontSize: '3em'}}>📦</div>
                  <h3>Drop Plugin Zip Here</h3>
              </div>
          )}

          {isLoading ? (
              <div className="plugin-grid" style={{ marginTop: '20px' }}>
                  {[1, 2, 3, 4, 5, 6].map(i => <PluginCardSkeleton key={i} />)}
              </div>
          ) : (
            <>
                {Object.keys(groupedPlugins).map(tag => (
                    <div key={tag} className="plugin-group">
                        <h4 className="group-header">{tag}</h4>
                        <div className="plugin-grid">
                        {groupedPlugins[tag].map(plugin => {
                            // Drivers (STT/TTS/Skill) are mutually exclusive, use active_in_group
                            const isGrouped = !!plugin.group_id;
                            // If grouped AND exclusive, use active_in_group. If standalone or independent group, use enabled.
                            const isSelected = ((plugin.group_id && plugin.group_exclusive) ? plugin.active_in_group : plugin.enabled) || false;
                            
                            // MVP Core Identification
                            // Dynamic Tag-based check
                            const isMvpCore = plugin.tags?.includes('mvp_kernel') || ['LLM Intelligence', 'LLM Core', 'Emotion Broker'].includes(plugin.name);

                            return (
                            <div 
                                key={plugin.id} 
                                className={`plugin-card ${isSelected ? 'active-card' : ''} ${isMvpCore ? 'mvp-core-card' : ''} clickable`}
                                onClick={(e) => {
                                    e.stopPropagation();

                                    // [UX Fix] Allow opening settings if selected OR if it has a valid config schema
                                    if (!isSelected && !plugin.config_schema) return;

                                    if (plugin.name === 'LLM Intelligence' || plugin.name === 'LLM Core') {
                                        if (onOpenLLMSettings) {
                                            onOpenLLMSettings();
                                        }
                                    } else if (plugin.name === 'Emotion Broker') {
                                        return;
                                    } else {
                                        setConfigPlugin(plugin);
                                    }
                                }}
                            >
                                {/* Row 1: Icon + Name + Toggle */}
                                <div className="card-top-row">
                                    <div className="header-left">
                                        <span className="plugin-icon">
                                            {plugin.category === 'skill' ? '📦' : 
                                             plugin.category === 'system' ? '⏰' : 
                                             plugin.category === 'tts' ? '🗣️' : '🎙️'}
                                        </span>
                                        <h3 className="plugin-title-inline">{plugin.name}</h3>
                                    </div>
                                    
                                    <div onClick={(e) => e.stopPropagation()}>
                                        {transitStates[plugin.id] ? (
                                            <div className="plugin-transit-state">
                                                <span className="spinner-small"></span>
                                                <span className="transit-label">{transitStates[plugin.id].toUpperCase()}...</span>
                                            </div>
                                        ) : (
                                            <GalgameToggle 
                                                checked={isSelected} 
                                                onChange={(val) => handleToggle(plugin, val)}
                                                labelOn={isGrouped ? 'USE' : 'ON'}
                                                labelOff="OFF"
                                            />
                                        )}
                                    </div>
                                </div>

                                {/* Row 2: Badges */}
                                <div className="card-mid-row">
                                     <div className="badge-row">
                                        {isMvpCore && <span className="core-badge">MVP KERNEL</span>}
                                        {plugin.permissions && plugin.permissions.length > 0 && (
                                            <span className="perm-badge" title="Requires Permissions">🛡️</span>
                                        )}
                                     </div>
                                </div>
                                
                                {/* Row 3: Description */}
                                <p className="description">{plugin.description}</p>
                            </div>
                        )})}
                        </div>
                    </div>
                ))}
            </>
          )}
        </div>
      </div>

      {/* Config Modal */}
      {configPlugin && (
          <PluginConfigModal 
              plugin={configPlugin} 
              onClose={() => setConfigPlugin(null)} 
              onSave={handleSaveConfig}
          />
      )}
      
      {/* Permission Confirmation Modal */}
      {pendingPlugin && (
        <div className="modal-overlay" style={{zIndex: 1100}}>
          <div className="modal-content glass-panel" style={{maxWidth: '400px'}}>
            <h3>🛡️ Permission Request</h3>
            <p><strong>{pendingPlugin.name}</strong> requires the following permissions:</p>
            <ul className="perm-list" style={{textAlign: 'left', background: 'rgba(0,0,0,0.2)', padding: '10px', borderRadius: '8px', margin: '10px 0'}}>
                {pendingPlugin.permissions?.map(p => (
                    <li key={p} style={{color: '#ff6b6b', listStyle: 'none', paddingLeft: '20px', position: 'relative'}}>
                        <span style={{position:'absolute', left:0}}>⚠️</span> {p}
                    </li>
                ))}
            </ul>
            <p style={{fontSize: '0.9em', color: '#ccc'}}>Do you want to trust this plugin?</p>
            <div className="modal-actions">
                <button onClick={() => setPendingPlugin(null)} className="cancel-btn">Cancel</button>
                <button onClick={handleConfirmPermission} className="save-btn" style={{background: '#ff4757'}}>Allow & Enable</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default PluginStoreModal;
