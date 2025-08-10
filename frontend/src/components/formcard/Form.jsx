"use client"
import React, { useState } from "react"
import ImageUp from "./ImageUp"
import { Button } from "../../app/ui/button"
import { useEffect } from "react"
import { supabase } from "../../lib/supabaseClient"

function Form() {
  const [formData, setFormData] = useState({
    title: "",
    category: "",
    max_participants: "",
    description: "",
    start_date: "",
    end_date: "",
    close_registration: "",
    is_team_based: "",
    type: "",
    poster_competition: "",
  })

  const handleChange = (e) => {
    const { name, value } = e.target

    if (name === "is_team_based") {
      setFormData({ ...formData, [name]: value === "true" })
    } else {
      setFormData({ ...formData, [name]: value })
    }
  }

  const handleImageChange = (url) => {
    setFormData({ ...formData, poster_competition: url })
  }

  const handleSubmit = async (e) => {
    e.preventDefault()

    const data = new FormData()
    data.append("title", formData.title)
    data.append("category", formData.category)
    data.append("description", formData.description)
    data.append("start_date", formData.start_date)
    data.append("end_date", formData.end_date)
    data.append("close_registration", formData.close_registration)
    data.append("max_participants", parseInt(formData.max_participants))
    data.append("is_team_based", formData.is_team_based === true)
    data.append("type", formData.type)

    // ✅ GANTI INI
    if (formData.poster_competition) {
      data.append("poster_competition", formData.poster_competition)
    }

    try {
      const token =
        typeof window !== "undefined"
          ? localStorage.getItem("access_token")
          : null

      if (!token) {
        alert("❌ No token found. Please login first.")
        return
      }

      const res = await fetch("http://127.0.0.1:8000/api/competitions/", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: data,
      })

      const result = await res.json()

      if (res.ok) {
        alert("✅ Competition added successfully!")
        console.log("Success response:", result)

        // Reset form
        setFormData({
          title: "",
          category: "",
          max_participants: "",
          description: "",
          start_date: "",
          end_date: "",
          close_registration: "",
          is_team_based: "",
          type: "",
          poster_competition: "", // ✅ Reset
        })

        window.location.href = "/dashboard/history"
      } else {
        console.error("❌ POST failed:", result)
        alert(
          `❌ Error: ${result.detail || result.error || "Something went wrong"}`
        )
      }
    } catch (error) {
      console.error("❌ Fetch error:", error)
      alert("❌ Failed to connect to the API.")
    }
  }

  useEffect(() => {
    const getSession = async () => {
      const {
        data: { session },
        error,
      } = await supabase.auth.getSession()

      if (error) {
        console.error("Gagal ambil session", error)
      } else if (session?.user) {
        console.log("✅ UID admin kamu adalah:", session.user.id)
      }
    }

    getSession()
  }, [])

  return (
    <div className="w-300 h-auto bg-gradient-to-tl py-10 mt-5 from-blue-500 rounded-4xl">
      <form
        onSubmit={handleSubmit}
        className="px-5 text-2xl grid grid-cols-1 md:grid-cols-2 gap-6"
      >
        <div className="flex flex-col">
          <label>Title / Name of Competition</label>
          <input
            type="text"
            name="title"
            value={formData.title}
            className="w-full h-30 mt-2 border rounded-2xl px-5 py-2"
            placeholder="Competition Title"
            onChange={handleChange}
            required
          />

          <label className="mt-5">Category</label>
          <select
            name="category"
            value={formData.category}
            onChange={handleChange}
            className="w-full mt-2 border rounded-2xl px-5 py-2"
            required
          >
            <option value="">Select Category</option>
            <option value="Technology">Technology</option>
            <option value="Business">Business</option>
            <option value="Art">Art & Design</option>
            <option value="Science">Science</option>
            <option value="other">Other</option>
          </select>

          <label className="mt-5">Max Participants</label>
          <input
            type="number"
            name="max_participants"
            value={formData.max_participants}
            className="w-full h-30 mt-2 border rounded-2xl px-5 py-2"
            placeholder="Example: 5"
            onChange={handleChange}
            required
          />

          <label className="mt-5">Type</label>
          <select
            name="type"
            value={formData.type}
            className="w-full h-30 mt-2 border rounded-2xl px-5 py-2"
            onChange={handleChange}
            required
          >
            <option value="">-- Select Type --</option>
            <option value="Team">Team</option>
            <option value="Individual">Individual</option>
          </select>

          <label className="mt-5">Team Based?</label>
          <select
            name="is_team_based"
            value={formData.is_team_based.toString()}
            className="w-full h-30 mt-2 border rounded-2xl px-5 py-2"
            onChange={handleChange}
            required
          >
            <option value="">-- Select Option --</option>
            <option value="true">Yes (Team)</option>
            <option value="false">No (Individual)</option>
          </select>

          <label className="mt-5">Competition Poster</label>
          <ImageUp onImageSelect={handleImageChange} />

          <label className="mt-5">Description</label>
          <textarea
            name="description"
            value={formData.description}
            className="w-full mt-2 border rounded-2xl px-5 py-4"
            placeholder="Competition Description"
            rows={4}
            onChange={handleChange}
            required
          />
        </div>

        <div className="flex flex-col">
          <label className="mb-5 text-4xl">Pick the Dates</label>

          <label>Start Date</label>
          <input
            type="datetime-local"
            name="start_date"
            value={formData.start_date}
            className="w-full mt-2 border rounded-2xl px-5 py-2"
            onChange={handleChange}
            required
          />

          <label className="mt-5">End Date</label>
          <input
            type="datetime-local"
            name="end_date"
            value={formData.end_date}
            className="w-full mt-2 border rounded-2xl px-5 py-2"
            onChange={handleChange}
            required
          />

          <label className="mt-5">Close Registration</label>
          <input
            type="datetime-local"
            name="close_registration"
            value={formData.close_registration}
            className="w-full mt-2 border rounded-2xl px-5 py-2"
            onChange={handleChange}
            required
          />

          <div className="mt-10">
            <Button
              type="submit"
              className="w-full bg-white text-black hover:text-white"
            >
              Submit
            </Button>
          </div>
        </div>
      </form>
    </div>
  )
}

export default Form
