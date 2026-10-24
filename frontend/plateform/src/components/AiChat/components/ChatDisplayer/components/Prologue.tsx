import AnswerAwartar from "../../../assets/img/answerAwartar.png";
const Prologue = ({
  data,
  className,
  style
}: {
  data: string;
  className?: string;
  style?: any;
}) => {
  return (
    <div
      className="flex w-full items-start h-fit pt-[16px] px-[16px]"
      style={style || {}}
    >
      <img
        src={AnswerAwartar}
        width={28}
        height={28}
        className={` ${className ? className : "mr-[20px]"}`}
      />
      <div className="bg-white px-[16px] py-[16px] box-border rounded-tl-[2px] rounded-tr-[6px] rounded-br-[6px] rounded-bl-[6px]">
        <div>{data}</div>
      </div>
    </div>
  );
};

export default Prologue;
