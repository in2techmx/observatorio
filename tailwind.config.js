/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            fontFamily: {
                sans: ['Rajdhani', 'sans-serif'],
                mono: ['Rajdhani', 'monospace'], // Cyberpunk style often uses same font
                display: ['Rajdhani', 'sans-serif'],
            },
            colors: {
                cyan: {
                    400: '#22d3ee',
                    500: '#06b6d4',
                    900: '#164e63',
                },
                magenta: {
                    400: '#e879f9',
                    500: '#d946ef',
                },
            },
        },
    },
    plugins: [],
}
