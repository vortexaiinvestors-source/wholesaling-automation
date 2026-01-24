'use client'

import { useState } from 'react'
import Link from 'next/link'
import axios from 'axios'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3000'

export default function SignupPage() {
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    phone: '',
    budget_min: '',
    budget_max: '',
    locations: [],
    categories: []
  })

  const [submitted, setSubmitted] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const categoryOptions = [
    { value: 'real-estate', label: 'Real Estate' },
    { value: 'vehicles', label: 'Vehicles' },
    { value: 'heavy-equipment', label: 'Heavy Equipment' },
    { value: 'luxury-items', label: 'Luxury Items' },
    { value: 'business-assets', label: 'Business Assets' },
    { value: 'wholesale', label: 'Wholesale Products' }
  ]

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const response = await axios.post(`${API_URL}/api/buyers`, formData)
      setSubmitted(true)
    } catch (err) {
      if (err.response?.status === 409) {
        setError('This email is already registered!')
      } else {
        setError(err.response?.data?.error || 'Failed to register. Please try again.')
      }
    } finally {
      setLoading(false)
    }
  }

  const handleCategoryToggle = (category) => {
    setFormData(prev => ({
      ...prev,
      categories: prev.categories.includes(category)
        ? prev.categories.filter(c => c !== category)
        : [...prev.categories, category]
    }))
  }

  const handleLocationAdd = (e) => {
    if (e.key === 'Enter' && e.target.value.trim()) {
      e.preventDefault()
      const location = e.target.value.trim()
      if (!formData.locations.includes(location)) {
        setFormData(prev => ({
          ...prev,
          locations: [...prev.locations, location]
        }))
      }
      e.target.value = ''
    }
  }

  const removeLocation = (location) => {
    setFormData(prev => ({
      ...prev,
      locations: prev.locations.filter(l => l !== location)
    }))
  }

  if (submitted) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-purple-600 via-indigo-600 to-blue-700 flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-white rounded-2xl shadow-2xl p-8 text-center">
          <div className="text-6xl mb-4">🎉</div>
          <h2 className="text-3xl font-bold mb-4">You're All Set!</h2>
          <p className="text-gray-600 mb-6">
            We'll start sending you deals that match your preferences via email and SMS.
          </p>
          <div className="space-y-3">
            <Link href="/deals" className="block bg-purple-600 text-white px-6 py-3 rounded-lg hover:bg-purple-700 transition font-semibold">
              Browse Current Deals
            </Link>
            <Link href="/" className="block border-2 border-purple-600 text-purple-600 px-6 py-3 rounded-lg hover:bg-purple-50 transition font-semibold">
              Back to Home
            </Link>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-600 via-indigo-600 to-blue-700 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-2xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <Link href="/" className="text-3xl font-bold text-white inline-block mb-4">
            VortexAI
          </Link>
          <h1 className="text-4xl font-bold text-white mb-2">Get Deal Alerts</h1>
          <p className="text-purple-100 text-lg">
            Tell us what you're looking for and we'll send you matching deals
          </p>
        </div>

        {/* Form */}
        <div className="bg-white rounded-2xl shadow-2xl p-8">
          {error && (
            <div className="mb-6 bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded-lg">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Name */}
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">
                Full Name <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                required
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full border border-gray-300 rounded-lg px-4 py-3 focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                placeholder="John Doe"
              />
            </div>

            {/* Email */}
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">
                Email Address <span className="text-red-500">*</span>
              </label>
              <input
                type="email"
                required
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                className="w-full border border-gray-300 rounded-lg px-4 py-3 focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                placeholder="john@example.com"
              />
            </div>

            {/* Phone */}
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">
                Phone Number (Optional)
              </label>
              <input
                type="tel"
                value={formData.phone}
                onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                className="w-full border border-gray-300 rounded-lg px-4 py-3 focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                placeholder="+1 (555) 123-4567"
              />
              <p className="mt-1 text-xs text-gray-500">For SMS alerts on high-score deals</p>
            </div>

            {/* Budget */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  Min Budget
                </label>
                <input
                  type="number"
                  value={formData.budget_min}
                  onChange={(e) => setFormData({ ...formData, budget_min: e.target.value })}
                  className="w-full border border-gray-300 rounded-lg px-4 py-3 focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                  placeholder="10000"
                />
              </div>
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  Max Budget
                </label>
                <input
                  type="number"
                  value={formData.budget_max}
                  onChange={(e) => setFormData({ ...formData, budget_max: e.target.value })}
                  className="w-full border border-gray-300 rounded-lg px-4 py-3 focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                  placeholder="500000"
                />
              </div>
            </div>

            {/* Categories */}
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-3">
                Interested Categories
              </label>
              <div className="grid grid-cols-2 gap-3">
                {categoryOptions.map(option => (
                  <button
                    key={option.value}
                    type="button"
                    onClick={() => handleCategoryToggle(option.value)}
                    className={`px-4 py-3 rounded-lg border-2 font-medium transition ${
                      formData.categories.includes(option.value)
                        ? 'border-purple-600 bg-purple-50 text-purple-700'
                        : 'border-gray-200 bg-white text-gray-700 hover:border-purple-300'
                    }`}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Locations */}
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">
                Preferred Locations
              </label>
              <input
                type="text"
                onKeyPress={handleLocationAdd}
                className="w-full border border-gray-300 rounded-lg px-4 py-3 focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                placeholder="Type a city/state and press Enter"
              />
              <p className="mt-1 text-xs text-gray-500">Press Enter to add each location</p>
              
              {formData.locations.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-2">
                  {formData.locations.map((location, idx) => (
                    <span
                      key={idx}
                      className="bg-purple-100 text-purple-700 px-3 py-1 rounded-full text-sm flex items-center gap-2"
                    >
                      {location}
                      <button
                        type="button"
                        onClick={() => removeLocation(location)}
                        className="hover:text-purple-900"
                      >
                        ✕
                      </button>
                    </span>
                  ))}
                </div>
              )}
            </div>

            {/* Submit */}
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-gradient-to-r from-purple-600 to-indigo-600 text-white px-6 py-4 rounded-lg font-bold text-lg hover:from-purple-700 hover:to-indigo-700 transition shadow-lg disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Signing Up...' : 'Start Getting Deal Alerts →'}
            </button>
          </form>

          <p className="mt-6 text-center text-sm text-gray-500">
            Already signed up? <Link href="/deals" className="text-purple-600 font-semibold hover:underline">Browse Deals</Link>
          </p>
        </div>
      </div>
    </div>
  )
}
