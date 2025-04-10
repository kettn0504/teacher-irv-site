import React, { useState } from 'react';

export default function TeacherIRV() {
  const [form, setForm] = useState({ name: '', email: '', message: '' });

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    alert('感謝您的來信，我們會盡快與您聯絡！');
    setForm({ name: '', email: '', message: '' });
  };

  return (
    <div className="bg-white text-gray-800 font-sans p-6 max-w-4xl mx-auto space-y-10">
      <header className="text-center">
        <img
          src="/your-photo.jpg"
          alt="IRV"
          className="w-32 h-32 rounded-full mx-auto mb-4"
        />
        <h1 className="text-4xl font-bold">TEACHER IRV</h1>
        <p className="text-xl text-blue-700 mt-2">專業私人家教</p>
      </header>

      <section>
        <h2 className="text-2xl font-semibold border-b pb-2">About Me</h2>
        <p className="mt-2">
          現職專業兒美教師，何嘉仁2023年全國教師試教競賽第一名，線上教學時數2000小時以上，具備多年教學與家教經驗，熟悉中英雙語語言差異。
        </p>
      </section>

      <section>
        <h2 className="text-2xl font-semibold border-b pb-2">教學成效</h2>
        <ul className="list-disc list-inside space-y-1 mt-2">
          <li>帶領AS/AD症狀學生通過全民英檢中級</li>
          <li>協助學生短期內將托福寫作從14分提升至21分</li>
          <li>成功輔導數位學生考上翻譯所（如木翻、輔大）</li>
        </ul>
      </section>

      <section className="grid md:grid-cols-2 gap-6">
        <div>
          <h2 className="text-2xl font-semibold border-b pb-2">使用語言</h2>
          <ul className="list-disc list-inside mt-2">
            <li>English（可全英語教學）</li>
            <li>TOEIC 945 / IELTS 7.5</li>
            <li>Mandarin Chinese</li>
          </ul>
        </div>

        <div>
          <h2 className="text-2xl font-semibold border-b pb-2">教學特色</h2>
          <ul className="list-disc list-inside mt-2">
            <li>耐心教學，重理解與應用</li>
            <li>發音矯正、香港/台灣學生音型調整</li>
            <li>中英雙語對照指導，幫助學生突破學習盲點</li>
          </ul>
        </div>
      </section>

      <section className="grid md:grid-cols-2 gap-6">
        <div>
          <h2 className="text-2xl font-semibold border-b pb-2">教學專長</h2>
          <ul className="list-disc list-inside mt-2">
            <li>文法解析與考題技巧</li>
            <li>自然發音與口說練習</li>
            <li>翻譯所備考（限預約）</li>
          </ul>
        </div>
        <div>
          <h2 className="text-2xl font-semibold border-b pb-2">學歷背景</h2>
          <p className="mt-2">國立中興大學 外國語文學系（2005-2009）</p>
        </div>
      </section>

      <section className="border-t pt-6">
        <h2 className="text-2xl font-semibold mb-4 text-center">聯絡我</h2>
        <form onSubmit={handleSubmit} className="space-y-4 max-w-md mx-auto">
          <input
            type="text"
            name="name"
            placeholder="您的姓名"
            value={form.name}
            onChange={handleChange}
            required
            className="w-full p-2 border rounded"
          />
          <input
            type="email"
            name="email"
            placeholder="Email 地址"
            value={form.email}
            onChange={handleChange}
            required
            className="w-full p-2 border rounded"
          />
          <textarea
            name="message"
            placeholder="請輸入您的訊息"
            rows="4"
            value={form.message}
            onChange={handleChange}
            required
            className="w-full p-2 border rounded"
          ></textarea>
          <button type="submit" className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">
            送出
          </button>
        </form>
      </section>

      <footer className="text-center border-t pt-4">
        <p>聯絡方式：LINE ID：irvwang｜Email：kettn0504@gmail.com</p>
        <p className="text-sm mt-2">服務地區：台北市 / 新北市 / 線上教學皆可</p>
      </footer>
    </div>
  );
}
