import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import Layout from '../../components/Layout';
import { submitChecklist } from '../../api/api';
import { FiCheckSquare, FiImage, FiSend, FiVideo } from 'react-icons/fi';
import { useAuth } from '../../context/AuthContext';

const checklists = {
  'Solar Installation': [
    'Inspect installation area',
    'Install mounting brackets',
    'Connect solar panels',
    'Configure inverter',
    'Test system output'
  ],
  'CCTV Installation': [
    'Install cameras',
    'Configure recording device',
    'Test camera view',
    'Setup mobile monitoring'
  ],
  'Fire Detection Alarm Systems': [
    'Install sensors',
    'Wire control panel',
    'Test detection',
    'Configure alerts'
  ],
  'Air Conditioning Services': [
    'Inspect unit',
    'Check refrigerant levels',
    'Clean filters',
    'Test cooling performance'
  ]
};

const maintenanceProfiles = [
  {
    value: 'commercial_area',
    label: 'Commercial Area',
    intervalDays: 90,
    description: 'High-traffic or high-dust sites that should be reviewed every 3 months.'
  },
  {
    value: 'dust_free_area',
    label: 'Dust-Free Area',
    intervalDays: 180,
    description: 'Controlled or cleaner environments that can wait 6 months.'
  },
  {
    value: 'standard_area',
    label: 'Standard Area',
    intervalDays: 120,
    description: 'Balanced default for typical sites when the environment is neither extreme.'
  }
];

export default function TechnicianChecklist() {
  const [searchParams] = useSearchParams();
  const jobId = searchParams.get('jobId') || searchParams.get('ticketId') || 1;
  const { user } = useAuth();
  const techName = user?.username || 'Ade Johnson';
  const [serviceType, setServiceType] = useState('Solar Installation');
  const [completed, setCompleted] = useState({});
  const [techNotes, setTechNotes] = useState('');
  const [photos, setPhotos] = useState([]);
  const [videos, setVideos] = useState([]);
  const [maintenanceRequired, setMaintenanceRequired] = useState(true);
  const [maintenanceProfile, setMaintenanceProfile] = useState('');
  const [maintenanceIntervalDays, setMaintenanceIntervalDays] = useState('');
  const [maintenanceNotes, setMaintenanceNotes] = useState('');
  const [warrantyProvided, setWarrantyProvided] = useState(true);
  const [warrantyPeriodDays, setWarrantyPeriodDays] = useState('30');
  const [warrantyNotes, setWarrantyNotes] = useState('');
  const [message, setMessage] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const steps = checklists[serviceType] || [];
  const selectedMaintenanceProfile = maintenanceProfiles.find((item) => item.value === maintenanceProfile);
  const resolvedIntervalDays = maintenanceRequired
    ? Number(maintenanceIntervalDays || selectedMaintenanceProfile?.intervalDays || 0)
    : 0;

  const toggleStep = (index) => {
    setCompleted(prev => ({
      ...prev,
      [index]: !prev[index]
    }));
  };

  const addPhoto = () => {
    const photoUrl = `job${jobId}-photo-${photos.length + 1}.jpg`;
    setPhotos(prev => [...prev, photoUrl]);
  };

  const addVideo = () => {
    const videoUrl = `job${jobId}-video-${videos.length + 1}.mp4`;
    setVideos(prev => [...prev, videoUrl]);
  };

  const handleSubmit = async () => {
    if (steps.some((_, i) => !completed[i])) {
      setMessage('Please complete all checklist items.');
      return;
    }
    if (maintenanceRequired && !maintenanceProfile) {
      setMessage('Select a maintenance profile so management can schedule the next service.');
      return;
    }
    if (warrantyProvided && (!warrantyPeriodDays || Number(warrantyPeriodDays) <= 0)) {
      setMessage('Enter a valid warranty coverage period.');
      return;
    }
    setSubmitting(true);
    setMessage('Submitting checklist...');
    try {
      const proofMedia = [
        ...photos.map((photo) => ({ type: 'photo', name: photo, url: photo })),
        ...videos.map((video) => ({ type: 'video', name: video, url: video }))
      ];
      await submitChecklist({
        jobId,
        serviceType,
        completed,
        notes: techNotes,
        photos,
        videos,
        proof_media: proofMedia,
        maintenance_required: maintenanceRequired,
        maintenance_profile: maintenanceRequired ? maintenanceProfile : null,
        maintenance_interval_days: maintenanceRequired ? resolvedIntervalDays : null,
        maintenance_notes: maintenanceNotes,
        warranty_provided: warrantyProvided,
        warranty_period_days: warrantyProvided ? Number(warrantyPeriodDays) : null,
        warranty_notes: warrantyNotes
      });
      setMessage('Checklist submitted successfully!');
      setTimeout(() => {
        setMessage('');
        // Navigate back or reset
      }, 3000);
    } catch (error) {
      setMessage('Failed to submit checklist.');
    }
    setSubmitting(false);
  };

  const progress = steps.length > 0 ? Object.keys(completed).filter(k => completed[k]).length / steps.length * 100 : 0;

  return (
    <Layout>
      <div className="mb-8">
        <h2 className="text-2xl font-semibold text-slate-800 flex items-center gap-3 mb-4">
          <FiCheckSquare className="text-emerald-500" size={28} />
          Digital Checklist - Job #{jobId}
        </h2>
        <div className="flex gap-4 mb-6">
          <select 
            value={serviceType} 
            onChange={(e) => setServiceType(e.target.value)}
            className="px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
          >
            {Object.keys(checklists).map(type => (
              <option key={type} value={type}>{type}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Progress */}
      <div className="mb-8 p-6 bg-gradient-to-r from-emerald-500 to-green-600 text-white rounded-2xl shadow-lg">
        <div className="flex items-center justify-between mb-2">
          <span>Completion Progress</span>
          <span className="font-bold">{Math.round(progress)}%</span>
        </div>
        <div className="w-full bg-white/20 rounded-full h-3">
          <div 
            className="bg-white h-3 rounded-full transition-all duration-500" 
            style={{width: `${progress}%`}}
          ></div>
        </div>
      </div>

      {/* Checklist Steps */}
      <div className="bg-white rounded-2xl shadow-sm border mb-8">
        <div className="p-6 border-b border-slate-200">
          <h3 className="text-lg font-semibold mb-2">Service Procedures ({steps.length} steps)</h3>
        </div>
        <div className="p-6 space-y-4">
          {steps.map((step, index) => (
            <div key={index} className="flex items-start gap-3 p-4 border border-slate-200 rounded-xl hover:shadow-sm transition group">
              <button
                onClick={() => toggleStep(index)}
                className={`flex-shrink-0 w-6 h-6 rounded-lg border-2 mt-0.5 flex items-center justify-center transition-all duration-200 mt-1 ${
                  completed[index]
                    ? 'bg-emerald-500 border-emerald-500 text-white shadow-md'
                    : 'border-slate-300 hover:border-slate-400'
                }`}
              >
                {completed[index] && <FiCheckSquare size={14} />}
              </button>
              <div className="flex-1 min-w-0">
                <label className="block text-sm font-medium text-slate-900 mb-1">{step}</label>
                {completed[index] && (
                  <span className="text-xs bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded">Completed</span>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="mb-8 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">Maintenance Logic</p>
            <h3 className="mt-2 text-lg font-semibold text-slate-900">Plan the next maintenance window before you close the job.</h3>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">
              This sends the next maintenance target to after-sales management once the job is completed.
            </p>
          </div>
          <label className="inline-flex items-center gap-3 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-medium text-emerald-900">
            <input
              type="checkbox"
              checked={maintenanceRequired}
              onChange={(e) => setMaintenanceRequired(e.target.checked)}
            />
            Create planned maintenance reminder
          </label>
        </div>

        <div className={`mt-5 ${maintenanceRequired ? 'opacity-100' : 'pointer-events-none opacity-50'}`}>
          <div className="grid gap-4 lg:grid-cols-3">
            {maintenanceProfiles.map((profile) => {
              const active = maintenanceProfile === profile.value;
              return (
                <button
                  key={profile.value}
                  type="button"
                  onClick={() => setMaintenanceProfile(profile.value)}
                  className={`rounded-2xl border p-4 text-left transition ${
                    active
                      ? 'border-emerald-500 bg-emerald-50 shadow-sm'
                      : 'border-slate-200 bg-slate-50 hover:border-slate-300 hover:bg-white'
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="text-sm font-semibold text-slate-900">{profile.label}</div>
                      <div className="mt-1 text-xs uppercase tracking-[0.2em] text-slate-400">
                        {profile.intervalDays} days cadence
                      </div>
                    </div>
                    <div className={`h-3 w-3 rounded-full ${active ? 'bg-emerald-500' : 'bg-slate-300'}`}></div>
                  </div>
                  <p className="mt-3 text-sm leading-6 text-slate-500">{profile.description}</p>
                </button>
              );
            })}
          </div>

          <div className="mt-5 grid gap-4 lg:grid-cols-[220px_1fr]">
            <div>
              <label className="mb-2 block text-sm font-semibold text-slate-900">Override Interval</label>
              <input
                type="number"
                min="1"
                value={maintenanceIntervalDays}
                onChange={(e) => setMaintenanceIntervalDays(e.target.value)}
                placeholder={selectedMaintenanceProfile ? String(selectedMaintenanceProfile.intervalDays) : 'Days'}
                className="w-full rounded-xl border border-slate-300 px-4 py-3 focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-200"
              />
            </div>
            <div>
              <label className="mb-2 block text-sm font-semibold text-slate-900">Maintenance Notes</label>
              <textarea
                value={maintenanceNotes}
                onChange={(e) => setMaintenanceNotes(e.target.value)}
                placeholder="Add why this cadence fits the site, seasonal concerns, dust level, customer constraints, or access notes."
                rows={3}
                className="w-full rounded-xl border border-slate-300 px-4 py-3 focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-200"
              />
            </div>
          </div>

          <div className="mt-4 rounded-2xl bg-slate-950 px-4 py-4 text-sm text-slate-200">
            {maintenanceRequired ? (
              resolvedIntervalDays > 0 ? (
                <>
                  Management will be alerted roughly <span className="font-semibold text-white">14 days before</span> the
                  next maintenance target, currently set to <span className="font-semibold text-white">{resolvedIntervalDays} days</span>
                  {' '}after completion.
                </>
              ) : (
                'Choose a site profile to calculate the next maintenance window.'
              )
            ) : (
              'No planned maintenance reminder will be created for this job.'
            )}
          </div>
        </div>
      </div>

      <div className="mb-8 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">Warranty Coverage</p>
            <h3 className="mt-2 text-lg font-semibold text-slate-900">Capture the warranty period before the job closes.</h3>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">
              This lets the after-sales team and clients see whether future issues are covered or should become standard support work.
            </p>
          </div>
          <label className="inline-flex items-center gap-3 rounded-2xl border border-sky-200 bg-sky-50 px-4 py-3 text-sm font-medium text-sky-900">
            <input
              type="checkbox"
              checked={warrantyProvided}
              onChange={(e) => setWarrantyProvided(e.target.checked)}
            />
            Warranty included
          </label>
        </div>

        <div className={`mt-5 grid gap-4 lg:grid-cols-[220px_1fr] ${warrantyProvided ? 'opacity-100' : 'pointer-events-none opacity-50'}`}>
          <div>
            <label className="mb-2 block text-sm font-semibold text-slate-900">Warranty Days</label>
            <input
              type="number"
              min="1"
              value={warrantyPeriodDays}
              onChange={(e) => setWarrantyPeriodDays(e.target.value)}
              className="w-full rounded-xl border border-slate-300 px-4 py-3 focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
            />
          </div>
          <div>
            <label className="mb-2 block text-sm font-semibold text-slate-900">Warranty Notes</label>
            <textarea
              value={warrantyNotes}
              onChange={(e) => setWarrantyNotes(e.target.value)}
              rows={3}
              placeholder="State coverage scope, exclusions, and anything the after-sales team should know."
              className="w-full rounded-xl border border-slate-300 px-4 py-3 focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
            />
          </div>
        </div>
      </div>

      {/* Notes & Photos */}
      <div className="grid lg:grid-cols-2 gap-6 mb-8">
        <div>
          <label className="block text-sm font-semibold text-slate-900 mb-3">Technician Notes</label>
          <textarea
            value={techNotes}
            onChange={(e) => setTechNotes(e.target.value)}
            placeholder="Describe work performed, issues found, materials used..."
            rows={5}
            className="w-full p-4 border border-slate-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-vertical"
          />
        </div>

        <div>
          <label className="block text-sm font-semibold text-slate-900 mb-3">
            Proof Uploads ({photos.length + videos.length})
          </label>
          <div className="space-y-2 mb-4">
            {photos.map((photo, i) => (
              <div key={i} className="w-full h-24 bg-gradient-to-br from-slate-200 to-slate-300 rounded-lg flex items-center justify-center text-sm text-slate-500 overflow-hidden">
                <span>{photo}</span>
              </div>
            ))}
            {videos.map((video, i) => (
              <div key={`${video}-${i}`} className="w-full h-24 bg-gradient-to-br from-sky-100 to-slate-200 rounded-lg flex items-center justify-center text-sm text-slate-600 overflow-hidden">
                <span>{video}</span>
              </div>
            ))}
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <button
              onClick={addPhoto}
              className="w-full flex items-center gap-2 px-4 py-3 bg-slate-100 hover:bg-slate-200 rounded-xl transition font-medium border-2 border-dashed border-slate-300 hover:border-slate-400"
            >
              <FiImage /> Add Photo
            </button>
            <button
              onClick={addVideo}
              className="w-full flex items-center gap-2 px-4 py-3 bg-sky-50 hover:bg-sky-100 rounded-xl transition font-medium border-2 border-dashed border-sky-300 hover:border-sky-400"
            >
              <FiVideo /> Add Video
            </button>
          </div>
        </div>
      </div>

      {/* Submit */}
      <div className="flex flex-col sm:flex-row gap-4 pt-6 border-t border-slate-200">
        <button
          onClick={handleSubmit}
          disabled={submitting || steps.some((_, i) => !completed[i])}
          className="flex-1 flex items-center justify-center gap-2 px-8 py-4 bg-gradient-to-r from-emerald-500 to-green-600 hover:from-emerald-600 hover:to-green-700 text-white font-semibold rounded-xl shadow-lg transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex-grow"
        >
          {submitting ? (
            <>
              <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
              Submitting...
            </>
          ) : (
            <>
              <FiSend size={20} />
              Submit Completed Checklist
            </>
          )}
        </button>
        {message && (
          <div className={`p-4 rounded-xl text-sm font-medium flex-1 flex items-center justify-center ${
            message.includes('success') ? 'bg-emerald-100 text-emerald-800 border-emerald-300 border' : 'bg-red-100 text-red-800 border-red-300 border'
          }`}>
            {message}
          </div>
        )}
      </div>
    </Layout>
  );
}
