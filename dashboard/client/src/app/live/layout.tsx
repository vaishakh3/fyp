import type { Metadata } from "next";

import Sidebar from "../../components/live/Sidebar";

export const metadata: Metadata = {
    title: "Live — DispatcherAI",
    icons: [{ rel: "icon", url: "/favicon.ico" }],
};

export default function RootLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <div className="flex h-[100dvh] max-h-[100dvh] min-w-[100dvw] max-w-[100dvw] overflow-hidden">
            <Sidebar />
            <div className="max-h-[100dvh] w-full">{children}</div>
        </div>
    );
}
