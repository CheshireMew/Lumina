import React, { useState, useEffect } from 'react';
import './PluginStoreModal.css';
import GalgameSelect from './GalgameSelect';
import GalgameToggle from './GalgameToggle';
import PluginConfigModal from './PluginConfigModal';

interface PluginItem {
  id: string;
  category: string;
  name: string;
  description: string;
  enabled: boolean;
  active_in_group: boolean;
  config_schema?: { 
      type: string; 
      key: string; 
      label: string;
      options?: {value: string; label: string}[]; 
      confirm_on_change?: boolean; 
  };
  current_value?: any; 
  func_tag?: string;
  is_driver?: boolean;
  service_url?: string;
  driver_id?: string;
  group_id?: string; 
  group_exclusive?: boolean; 
  permissions?: string[]; // [NEW]
  tags?: string[]; // [NEW] Dynamic Styling
}

interface PluginStoreModalProps {
  isOpen: boolean;
  onClose: () => void;
  onOpenLLMSettings?: () => void; // [NEW] Link to LLM Config
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
  const [plugins, setPlugins] = useState<PluginItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [configPlugin, setConfigPlugin] = useState<PluginItem | null>(null); // Plugin being configured
  
  // [NEW] Permission Modal State
  const [pendingPlugin, setPendingPlugin] = useState<PluginItem | null>(null);
  
  // [NEW] Drag & Drop State
  const [dragActive, setDragActive] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<string | null>(null); // "uploading", "success", "error"

  // Fetch Plugins
  const fetchPlugins = async () => {
    setLoading(true);
    try {
      const res = await fetch('http://localhost:8010/plugins/list');
      const data = await res.json();
      console.log("[PluginStore] Fetched plugins:", data);
      setPlugins(data || []); // data is already the array
    } catch (error) {
      console.error('Failed to fetch plugins:', error);
    } finally {
      // Small delay for smooth aesthetic transition
      setTimeout(() => setLoading(false), 600);
    }
  };

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
          const res = await fetch('http://localhost:8010/plugins/upload', {
              method: 'POST',
              body: formData
          });
          const data = await res.json();
          if (res.ok) {
              setUploadStatus("success");
              // Check if we need to show a restart prompt or confirm
              alert(`Plugin installed: ${data.id}\nPlease restart backend to load.`);
              // Ideally we trigger backend refresh logic if implemented
          } else {
              setUploadStatus("error");
              alert(`Upload failed: ${data.detail}`);
          }
      } catch (e: any) {
          console.error(e);
          setUploadStatus("error");
          alert("Upload error: " + e.message);
      } finally {
          setUploadStatus(null);
          // Refresh list anyway just in case hot reload works
          fetchPlugins();
      }
  };

  useEffect(() => {
    if (isOpen) fetchPlugins();
  }, [isOpen]);

  const executeToggle = async (plugin: PluginItem, newState: boolean) => {
    console.log(`[PluginStore] Executing Toggle ${plugin.id} to ${newState}`);
    
    // [OPTIMISTIC UPDATE]
    if (newState && plugin.group_id && plugin.group_exclusive) {
        setPlugins(prev => prev.map(p => {
            if (p.group_id === plugin.group_id) {
                return { 
                    ...p, 
                    active_in_group: p.id === plugin.id,
                    enabled: p.id === plugin.id 
                };
            }
            return p;
        }));
    }

    // 1. Skill (Search) - Legacy Category Check
    if (plugin.category === 'skill') {
         if (!newState) return;
         try {
            await fetch('http://localhost:8010/plugins/config/search', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ provider_id: plugin.id })
            });
        } catch(e) { console.error(e); }
    } 
    // 2. Driver (TTS/STT or Group)
    else if (plugin.is_driver && plugin.service_url) {
        if (!newState) return;
        
        let targetId = plugin.driver_id || plugin.id;
        try {
            await fetch(plugin.service_url, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ model_name: targetId })
            });
        } catch(e) { console.error(e); }
    }
    // 3. System / Default
    else {
        try {
            await fetch('http://localhost:8010/plugins/toggle/system', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ provider_id: plugin.id })
            });
        } catch(e) { console.error(e); }
    }

    // Refresh
    setTimeout(() => {
        fetchPlugins();
    }, 300); 
  };

  const handleToggle = (plugin: PluginItem, newState: boolean) => {
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

  const handleSaveConfig = async (key: string, value: string) => {
    if (!configPlugin) return;
    try {
        if (key === 'voiceprint_threshold' || configPlugin.id.startsWith('system.')) {
             await fetch('http://localhost:8010/plugins/config/system', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ key, value })
            });
        }
        else if (key === 'BRAVE_API_KEY') {
            await fetch('http://localhost:8010/plugins/config/brave-key', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ key, value })
            });
        }
        else if (key === 'fw_model_size') {
            // Updating model size -> Also Trigger Switch!
            if (configPlugin.service_url) {
                await fetch(configPlugin.service_url, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ model_name: value })
                });
            }
        }
        // [NEW] Group ID Update
        else if (key === '__group_id') {
             await fetch('http://localhost:8010/plugins/config/group', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ key: configPlugin.id, value: value })
            });
        }
        else if (key === '__category') {
             await fetch('http://localhost:8010/plugins/config/category', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ key: configPlugin.id, value: value })
            });
        }
        else if (key === '__group_behavior') {
            const targetGroup = configPlugin.group_id; 
            if(targetGroup) {
                 await fetch('http://localhost:8010/plugins/config/group_behavior', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ key: targetGroup, value: value })
                });
            }
        }
        
        fetchPlugins();
    } catch(e) { console.error(e); }
  };

  if (!isOpen) return null;

  const filteredPlugins = plugins.filter(p => p.category === activeTab);
  
  // Group by Function Tag
  const groupedPlugins: {[tag: string]: PluginItem[]} = {};
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

          {loading ? (
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
                            // If grouped, use active_in_group. If standalone, use enabled.
                            const isSelected = isGrouped ? plugin.active_in_group : plugin.enabled;
                            
                            // Always clickable now for "Advanced Group" setting
                            const hasConfig = !!plugin.config_schema;

                            // MVP Core Identification
                            // Dreaming/Reverie removed from Kernel as per user request (Optional)
                            // MVP Core Identification
                            // Dynamic Tag-based check
                            const isMvpCore = plugin.tags?.includes('mvp_kernel') || ['LLM Intelligence', 'LLM Core', 'Emotion Broker'].includes(plugin.name);

                            return (
                            <div 
                                key={plugin.id} 
                                className={`plugin-card ${isSelected ? 'active-card' : ''} ${isMvpCore ? 'mvp-core-card' : ''} clickable`}
                                onClick={(e) => {
                                    // Stop propagation
                                    e.stopPropagation();

                                    // Only allow opening settings if plugin is enabled
                                    if (!isSelected) return;

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
                                        <GalgameToggle 
                                            checked={isSelected} 
                                            onChange={(val) => handleToggle(plugin, val)}
                                            labelOn={isGrouped ? 'USE' : 'ON'}
                                            labelOff="OFF"
                                        />
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
              existingGroups={[...new Set(plugins.map(p => p.group_id).filter((g): g is string => !!g))]}
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
