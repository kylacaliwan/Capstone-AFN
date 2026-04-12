import { Link } from 'react-router-dom';

export default function Landing() {
  return (
    <div className="w-full min-h-screen bg-white">

      {/* NAVBAR */}
      <header className="sticky top-0 bg-white flex items-center justify-between px-8 py-4 shadow-sm">
        <div className="flex items-center gap-2">
          <img src="/logo.png" alt="logo" className="h-10" />
        </div>

        <div className="flex gap-4">
          <Link to="/login" className="text-slate-600 hover:text-blue-600">
            About Us
          </Link>
          
        </div>
      </header>

      {/* HERO SECTION */}
      <section
        className="h-[90vh] flex items-center justify-center bg-cover bg-center"
        style={{ backgroundImage: "url('/login-bg.jpg')" }}
      >
        <div className="bg-black/60 w-full h-full flex items-center">
          <div className="max-w-5xl mx-auto px-8 text-white">
            <h1 className="text-5xl font-bold leading-tight mb-6">
              Smarter Home Servicing Starts Here
            </h1>
            <p className="text-lg text-slate-200 mb-8 max-w-xl">
              Manage your solar systems, air conditioning, and CCTV services with ease.
              Book requests, track technicians, and stay in control—all in one simple platform.
            </p>

            <div className="flex gap-4">
              <Link
                to="/register"
                className="bg-blue-600 px-6 py-3 rounded-lg text-white font-semibold hover:bg-blue-700"
              >
                Get Started
              </Link>

              <Link
                to="/login"
                className="border border-white px-6 py-3 rounded-lg hover:bg-white hover:text-black"
              >
                Login
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* FEATURES */}
      <section className="py-20 px-8 bg-slate-50">
        <div className="max-w-6xl mx-auto text-center mb-12">
          <h2 className="text-3xl font-bold text-slate-800">
            Powerful Features
          </h2>
          <p className="text-slate-500 mt-2">
            Everything you need to manage services efficiently
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-8 max-w-6xl mx-auto">
          <div className="bg-white p-6 rounded-xl shadow">
            <h3 className="font-semibold text-lg mb-2">Service Management</h3>
            <p className="text-sm text-slate-500">
              Create and track service tickets بسهولة and efficiently.
            </p>
          </div>

          <div className="bg-white p-6 rounded-xl shadow">
            <h3 className="font-semibold text-lg mb-2">Technician Tracking</h3>
            <p className="text-sm text-slate-500">
              Monitor technician locations and job progress in real-time.
            </p>
          </div>

          <div className="bg-white p-6 rounded-xl shadow">
            <h3 className="font-semibold text-lg mb-2">After-Sales Support</h3>
            <p className="text-sm text-slate-500">
              Handle warranties, complaints, and maintenance seamlessly.
            </p>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 bg-blue-600 text-white text-center">
        <h2 className="text-3xl font-bold mb-4">
          Ready to get started?
        </h2>
        <p className="mb-6 text-blue-100">
          Create your account and start managing your services today.
        </p>

        <Link
          to="/register"
          className="bg-white text-blue-600 px-6 py-3 rounded-lg font-semibold hover:bg-slate-100"
        >
          Create Account
        </Link>
      </section>

      {/* FOOTER */}
      <footer className="text-center py-6 text-sm text-slate-500">
        © {new Date().getFullYear()} AFN Service Management. All rights reserved.
      </footer>
    </div>
  );
}