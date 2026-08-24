import {
  AbsoluteFill,
  Easing,
  Interactive,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

export type IntroProps = {
  companyName: string;
  tagline: string;
};

export const Intro: React.FC<IntroProps> = ({ companyName, tagline }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  return (
    <AbsoluteFill
      name="Fondo"
      className="items-center justify-center bg-[#0b1e3f] font-sans"
    >
      <Interactive.Div
        name="Resplandor"
        className="absolute h-[1400px] w-[1400px] rounded-full bg-[radial-gradient(circle,#1d4ed8_0%,rgba(11,30,63,0)_65%)]"
        style={{
          opacity: interpolate(frame, [0, 2 * fps], [0, 0.55], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: Easing.bezier(0.16, 1, 0.3, 1),
          }),
          scale: interpolate(frame, [0, 4 * fps], [0.7, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: Easing.bezier(0.16, 1, 0.3, 1),
            output: "perceptual-scale",
          }),
        }}
      />
      <Interactive.Div
        name="Nombre de la empresa"
        className="px-20 text-center text-[150px] font-bold leading-none tracking-tight text-white"
        style={{
          opacity: interpolate(
            frame,
            [0.5 * fps, 2 * fps, durationInFrames - 20, durationInFrames],
            [0, 1, 1, 0],
            {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
              easing: [
                Easing.bezier(0.16, 1, 0.3, 1),
                Easing.linear,
                Easing.bezier(0.16, 1, 0.3, 1),
              ],
            },
          ),
          scale: interpolate(frame, [0.5 * fps, 2.5 * fps], [0.92, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: Easing.bezier(0.16, 1, 0.3, 1),
            output: "perceptual-scale",
          }),
        }}
      >
        {companyName}
      </Interactive.Div>
      <Interactive.Div
        name="Línea de acento"
        className="mt-12 h-[6px] rounded-full bg-[#38bdf8]"
        style={{
          width: interpolate(frame, [2 * fps, 3.5 * fps], [0, 420], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: Easing.bezier(0.16, 1, 0.3, 1),
          }),
          opacity: interpolate(
            frame,
            [2 * fps, 2.5 * fps, durationInFrames - 20, durationInFrames],
            [0, 1, 1, 0],
            {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
              easing: [
                Easing.bezier(0.16, 1, 0.3, 1),
                Easing.linear,
                Easing.bezier(0.16, 1, 0.3, 1),
              ],
            },
          ),
        }}
      />
      <Interactive.Div
        name="Eslogan"
        className="mt-12 px-20 text-center text-[70px] font-medium text-[#c7d7f5]"
        style={{
          opacity: interpolate(
            frame,
            [3 * fps, 4.5 * fps, durationInFrames - 20, durationInFrames],
            [0, 1, 1, 0],
            {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
              easing: [
                Easing.bezier(0.16, 1, 0.3, 1),
                Easing.linear,
                Easing.bezier(0.16, 1, 0.3, 1),
              ],
            },
          ),
          translate: interpolate(
            frame,
            [3 * fps, 4.5 * fps],
            ["0px 120px", "0px 0px"],
            {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
              easing: Easing.bezier(0.16, 1, 0.3, 1),
            },
          ),
        }}
      >
        {tagline}
      </Interactive.Div>
    </AbsoluteFill>
  );
};
